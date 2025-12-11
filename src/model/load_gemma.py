from llama_cpp import Llama

llm = Llama(
    model_path="models/gemma-2-2b-it-Q5_K_M.gguf",
    n_ctx=8192,
    n_threads=4,
    n_batch=512,
    verbose=False
)

prompt = """<bos><start_of_turn>user
Write a catchy, engaging Instagram/Facebook ad (max 80 words) for this product.

Product: Wireless Bluetooth Earbuds
Description: Noise-cancelling, 30h battery, waterproof, under $50

Ad:<end_of_turn>
<start_of_turn>model
"""

output = llm(prompt, max_tokens=120, temperature=0.8, top_p=0.9, stop=["<end_of_turn>"])
ad = output["choices"][0]["text"].strip()

print("\n=== GENERATED AD ===\n")
print(ad)