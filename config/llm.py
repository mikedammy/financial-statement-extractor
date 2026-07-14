import os
import time
import random
import litellm
from dotenv import load_dotenv
from crewai import LLM
from functions.log_adder import add_log

load_dotenv()

# ─── DEFINE MODEL FALLBACK POOLS ──────────────────────────────────────────────
# If a model in this pool hits a 429, LiteLLM automatically shifts down to the next provider.
GROQ_MODELS_POOL = [
    "groq/llama-3.3-70b-versatile",
    "groq/llama-3.3-70b-versatile",
    "groq/qwen/qwen3.6-27b",          # Backup structure engine
    "gemini/gemini-2.5-flash"         # Ultimate fallback if Groq quotas are completely drained
]

# ─── GLOBAL LITELM RATE LIMIT INTERCEPTOR WITH MODEL SWAPPING ─────────────────
original_completion = litellm.completion

def patched_completion(*args, **kwargs):
    """Globally intercepts every completion call funneled through CrewAI.
    
    If a 429 or resource exhaust exception is triggered, it automatically hot-swaps 
    the active execution parameters to use the next fallback model provider in the sequence 
    and applies randomized backoff timing delays.

    Args:
        *args: LiteLLM sequential functional arguments.
        **kwargs: Request dictionary keys containing execution criteria (model, temperature).

    Returns:
        litellm.ModelResponse: The validated token generation stream package from the provider.

    Raises:
        Exception: If the fallback pool is completely exhausted or encounters unrecoverable errors.
    """
    current_model = kwargs.get("model", "")
    delay = 3.0
    max_retries = 6

    for attempt in range(max_retries):
        try:
            return original_completion(*args, **kwargs)
        except Exception as e:
            err_str = str(e)
            
            # Catch standard multi-provider usage limits or resource blocks
            if any(k in err_str or k in err_str.lower() for k in ["429", "resource_exhausted", "rate_limit", "quota exceeded"]):
                
                if current_model in GROQ_MODELS_POOL:
                    current_index = GROQ_MODELS_POOL.index(current_model)
                    
                    if current_index + 1 < len(GROQ_MODELS_POOL):
                        next_model = GROQ_MODELS_POOL[current_index + 1]
                        kwargs["model"] = next_model
                        current_model = next_model
                        
                        # Dynamically swap respective authentication tokens alongside the model target
                        if "gemini" in next_model:
                            kwargs["api_key"] = os.getenv("GEMINI_API_KEY")
                        elif "groq" in next_model:
                            kwargs["api_key"] = os.getenv("GROQ_API_KEY_TWO")

                        add_log(f"Model limit hit. Rerouting token payload to fallback layer: {next_model} (Attempt {attempt+1}/{max_retries})", level='warning', source='LLM')
                    else:
                        add_log("CRITICAL: All model options in the fallback pool have been completely exhausted.", level='critical', source='LLM')
                
                sleep_time = delay + random.uniform(0.5, 1.5)
                add_log(f"API Backpressure active. Thread sleeping for {sleep_time:.2f}s before fallback re-execution.", level='info', source='LLM')
                time.sleep(sleep_time)
                delay *= 1.5
            else:
                # Instantly raise application errors that aren't rate limits (e.g. invalid context syntax, bad auth keys)
                raise e
                
    raise Exception("Exceeded the maximum available retry iterations inside the LiteLLM Rate Limit Interceptor.")

# Actively apply the patch to the execution layer
litellm.completion = patched_completion
# ──────────────────────────────────────────────────────────────────────────────

# ─── CREWAI LLM INITIALIZATION ────────────────────────────────────────────────
groq_llama = LLM(
    model="groq/llama-3.3-70b-versatile",
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0.0
)

gemini_llm = LLM(
    model="gemini/gemini-2.5-flash",
    api_key=os.getenv("GEMINI_API_KEY"),
    temperature=0.0
)

cerebras_llama = LLM(
    model="cerebras/gpt-oss-120b",
    api_key=os.getenv("CEREBRAS_API_KEY"),
    temperature=0.0
)

os.environ["GITHUB_API_KEY"] = os.getenv("GITHUB_TOKEN", "")
github_llama = LLM(
    model="github/phi-4",
    temperature=0.0
)
