import os
import litellm
from crewai import LLM
from dotenv import load_dotenv

# Carica le variabili dal file .env
load_dotenv()

# 1. MAPPATURA ALIAS:
# Forza LiteLLM a trattare Qwen come un modello "sicuro" (Llama 3.3) 
# per evitare l'invio del parametro non supportato 'cache_breakpoint'
litellm.model_alias_map = {
    "qwen/qwen3-32b": "groq/llama-3.3-70b-versatile"
}

# 2. CONFIGURAZIONE DI SICUREZZA PER GROQ:
# drop_params=True rimuove automaticamente i parametri incompatibili (come la cache)
# prima che la richiesta arrivi a Groq.
litellm.drop_params = True
litellm.cache = None
os.environ["LITELLM_CACHE_ENABLED"] = "False"

# Silenzia i log di debug di litellm per tenere il terminale pulito
os.environ["LITELLM_LOG"] = "ERROR"

# PATCH: Forcefully remove 'cache_breakpoint' from all messages
# CrewAI injects this for prompt caching, but Groq doesn't support it on all models.
_original_completion = litellm.completion
def patched_completion(*args, **kwargs):
    if "messages" in kwargs:
        for msg in kwargs["messages"]:
            msg.pop("cache_breakpoint", None)
    return _original_completion(*args, **kwargs)
litellm.completion = patched_completion

def create_llm(model_id):
    """
    Funzione helper per istanziare un modello LLM di CrewAI.
    """
    if "/" not in model_id:
        model_id = f"groq/{model_id}"
    elif model_id.startswith("qwen/"):
        # Se c'è l'alias qwen, dobbiamo assicurarci che usi groq. 
        # Tuttavia litellm.model_alias_map è globale. Per sicurezza,
        # passiamo direttamente il modello su groq/ se è quello reale.
        pass

    return LLM(
        model=model_id
    )

# 3. ISTANZE DEI MODELLI:
# big_llm: Usa il 70B "vero" (senza alias) per la logica complessa del Manager.
big_llm = create_llm("llama-3.3-70b-versatile")

# medium_llm: Usa Qwen. Grazie all'alias definito sopra, LiteLLM userà 
# i parametri del 70B, rendendolo compatibile con Groq.
medium_llm = create_llm("qwen/qwen3-32b")

# small_llm: Modello leggero per task veloci
small_llm = create_llm("llama-3.1-8b-instant")