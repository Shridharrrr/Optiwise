"""Quick smoke test — run with: python test_rag.py"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from utils.rag_utils import store_document, search_documents, list_user_documents, delete_user_document

TEST_UID = "test_user_rag"
TEST_SOURCE = "test_note.txt"
TEST_TEXT = """
Newton's Laws of Motion:
1. An object at rest stays at rest unless acted upon by a force.
2. Force equals mass times acceleration (F = ma).
3. For every action there is an equal and opposite reaction.

Kinematics:
Displacement, velocity, and acceleration describe motion.
Average velocity = displacement / time.
"""

print("=== RAG Smoke Test ===\n")

# 1. Store
print("1. Storing document...")
count = store_document(TEST_UID, TEST_TEXT, TEST_SOURCE)
print(f"   Stored {count} chunks ✅\n")

# 2. Search
print("2. Searching for 'force and acceleration'...")
results = search_documents(TEST_UID, "force and acceleration", k=2)
if results:
    for r in results:
        print(f"   RESULT: {r[:120]}...")
    print("   Search works ✅\n")
else:
    print("   ❌ No results returned!\n")

# 3. List
print("3. Listing documents...")
docs = list_user_documents(TEST_UID)
print(f"   Found: {docs}")
print(f"   List works ✅\n" if docs else "   ❌ No documents listed!\n")

# 4. Delete
print("4. Deleting test document...")
deleted = delete_user_document(TEST_UID, TEST_SOURCE)
print(f"   Deleted {deleted} chunks ✅\n")

# 5. Verify deletion
print("5. Verifying deletion...")
results_after = search_documents(TEST_UID, "Newton laws", k=2)
print(f"   Results after delete: {len(results_after)} (should be 0) {'✅' if not results_after else '❌'}")

print("\n=== Done ===")
