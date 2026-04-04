# TODO: Fix Mistral ImportError
## Approved Plan Steps

- [x] Step 1: Update requirements.txt to add `mistralai`
- [x] Step 2: Install dependencies with `pip install -r requirements.txt`
- [x] Step 3: Verify fix (check imports or run without full app start)
- [x] Step 4: Complete task
- [x] Step 5: Fix LLM.py import to `from mistralai.client import Mistral` (version 2.3.0 change)
- [x] Step 6: Add/install python-dotenv for load_dotenv()
