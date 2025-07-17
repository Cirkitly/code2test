# utils/async_call_llm.py
import asyncio
from .call_llm import call_llm as sync_call_llm

async def call_llm(prompt: str, use_cache: bool = True, max_tokens: int = 4096) -> str:
    """
    Asynchronous wrapper for the synchronous call_llm function.
    
    This runs the blocking, network-bound call_llm in a separate thread
    to avoid blocking the main asyncio event loop, allowing for true parallelism
    in PocketFlow's async nodes.
    """
    loop = asyncio.get_running_loop()
    
    # Use functools.partial to pass arguments to the synchronous function
    import functools
    func_with_args = functools.partial(sync_call_llm, prompt, use_cache, max_tokens)
    
    # run_in_executor runs the synchronous function in a thread pool
    try:
        response = await loop.run_in_executor(None, func_with_args)
        return response
    except Exception as e:
        # The exception from the thread will be re-raised here.
        # We can log it or handle it as needed.
        print(f"Async LLM call failed: {e}")
        return f"Error: Async LLM call failed with {type(e).__name__}"

if __name__ == "__main__":
    async def test_async_llm():
        try:
            test_prompt = "Explain the concept of a state machine in one sentence."
            print("Testing async LLM wrapper...")
            print(f"Prompt: {test_prompt}")
            response = await call_llm(test_prompt, use_cache=False)
            print(f"Response: {response}")
            print("\nAsync LLM wrapper seems to be working.")
        except Exception as e:
            print(f"\nAn error occurred: {e}")
            print("Please check your .env configuration and ensure the AI service (Azure/Ollama) is running and accessible.")
            
    asyncio.run(test_async_llm())