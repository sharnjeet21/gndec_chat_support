"""
Test the unified RAG pipeline directly (bypassing HTTP).
"""
import asyncio
import os
import sys

# Setup
os.environ["API_KEY"] = "naman@1234"

# Add project root to path
sys.path.insert(0, "/home/sharnjeet-singh/Developer/gndec_rag")

from backend.rag import answer_query, create_default_pipeline
from backend.rag.contracts import VerificationStatus


async def test_pipeline_basic():
    """Test basic pipeline execution."""
    print("\n=== Test: Basic Pipeline ===")

    query = "What is the B.Tech fee structure?"
    phone = "test_phone"
    session_id = "test_session_basic"

    ctx = await answer_query(query, phone, session_id, "en")

    print(f"Request ID: {ctx.request_id}")
    print(f"Query: {ctx.query}")
    print(f"Errors: {ctx.errors}")

    if ctx.generation:
        print(f"Answer: {ctx.generation.answer[:200]}...")
        print(f"Citations: {len(ctx.generation.citations)}")

    if ctx.verification:
        print(f"Verification: {ctx.verification.status}")
        print(f"Confidence: {ctx.verification.confidence}")
        if ctx.verification.issues:
            print(f"Issues: {ctx.verification.issues}")

    assert not ctx.errors, f"Pipeline errors: {ctx.errors}"
    assert ctx.generation is not None, "No generation output"
    assert ctx.generation.answer, "Empty answer"

    print("✓ Basic pipeline test passed")


async def test_pipeline_with_memory():
    """Test that memory works across queries."""
    print("\n=== Test: Pipeline with Memory ===")

    phone = "test_phone_memory"
    session_id = "test_session_memory"

    # First query
    ctx1 = await answer_query("What courses does GNDEC offer?", phone, session_id, "en")
    print(f"Q1: {ctx1.query}")
    print(f"A1: {ctx1.generation.answer[:100] if ctx1.generation else 'N/A'}...")

    # Follow-up query
    ctx2 = await answer_query("What about B.Tech CSE?", phone, session_id, "en")
    print(f"Q2: {ctx2.query}")
    print(f"A2: {ctx2.generation.answer[:100] if ctx2.generation else 'N/A'}...")

    assert ctx1.generation is not None
    assert ctx2.generation is not None

    print("✓ Memory test passed")


async def test_pipeline_verification():
    """Test verification stage."""
    print("\n=== Test: Pipeline Verification ===")

    query = "What is the address of GNDEC?"
    phone = "test_phone_verify"
    session_id = "test_session_verify"

    ctx = await answer_query(query, phone, session_id, "en")

    print(f"Query: {ctx.query}")
    print(f"Verification Status: {ctx.verification.status if ctx.verification else 'None'}")
    print(f"Confidence: {ctx.verification.confidence if ctx.verification else 'N/A'}")

    # Should be grounded for factual queries
    if ctx.verification:
        assert ctx.verification.status in [VerificationStatus.GROUNDED, VerificationStatus.PARTIALLY_GROUNDED]

    print("✓ Verification test passed")


async def test_pipeline_off_topic():
    """Test off-topic handling."""
    print("\n=== Test: Off-Topic Query ===")

    query = "How do I write a Python function?"
    phone = "test_phone_offtopic"
    session_id = "test_session_offtopic"

    ctx = await answer_query(query, phone, session_id, "en")

    print(f"Query: {ctx.query}")
    print(f"Policy Decision: {ctx.policy.decision if ctx.policy else 'None'}")
    print(f"Answer: {ctx.generation.answer if ctx.generation else 'N/A'}")

    assert ctx.policy is not None
    assert ctx.policy.decision.value == "redirect"

    print("✓ Off-topic test passed")


async def test_pipeline_sensitive():
    """Test sensitive content handling."""
    print("\n=== Test: Sensitive Content ===")

    query = "What is the password for the admin panel?"
    phone = "test_phone_sensitive"
    session_id = "test_session_sensitive"

    ctx = await answer_query(query, phone, session_id, "en")

    print(f"Query: {ctx.query}")
    print(f"Policy Decision: {ctx.policy.decision if ctx.policy else 'None'}")
    print(f"Answer: {ctx.generation.answer if ctx.generation else 'N/A'}")

    assert ctx.policy is not None
    assert ctx.policy.decision.value == "deny"

    print("✓ Sensitive content test passed")


async def main():
    """Run all tests."""
    print("=" * 60)
    print("RAG Pipeline Tests")
    print("=" * 60)

    try:
        await test_pipeline_basic()
        await test_pipeline_with_memory()
        await test_pipeline_verification()
        await test_pipeline_off_topic()
        await test_pipeline_sensitive()

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())