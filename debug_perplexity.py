#!/usr/bin/env python
"""Debug script for Perplexity API calls.

This script tests the Perplexity API integration and prints detailed debug info.
"""

import asyncio
import os
import sys
import json

# Allow running from project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import httpx


async def test_raw_api():
    """Test the Perplexity API directly without the client wrapper."""
    api_key = os.getenv("PERPLEXITY_API_KEY", "")

    print("=" * 60)
    print("PERPLEXITY API DEBUG")
    print("=" * 60)

    # Check API key
    if not api_key:
        print("\n❌ PERPLEXITY_API_KEY not set in environment")
        print("   Set it with: export PERPLEXITY_API_KEY=your-key-here")
        return False

    print(f"\n✓ API Key found: {api_key[:10]}...{api_key[-4:]}")

    # Test the API endpoint
    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    # Simple test payload
    payload = {
        "model": "sonar",
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful assistant."
            },
            {
                "role": "user",
                "content": "What is the capital of France? Reply in one word."
            }
        ]
    }

    print(f"\n📤 Request URL: {url}")
    print(f"📤 Model: {payload['model']}")
    print(f"📤 Message: {payload['messages'][-1]['content']}")

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, headers=headers, json=payload)

            print(f"\n📥 Status Code: {response.status_code}")
            print(f"📥 Headers: {dict(response.headers)}")

            if response.status_code == 200:
                data = response.json()
                print(f"\n✓ SUCCESS - Response:")
                print(json.dumps(data, indent=2))

                # Check for expected fields
                print("\n📋 Response structure check:")
                print(f"   - choices: {'✓' if 'choices' in data else '✗'}")
                print(f"   - citations: {'✓' if 'citations' in data else '✗ (not present)'}")
                print(f"   - search_results: {'✓' if 'search_results' in data else '✗ (not present)'}")
                print(f"   - model: {data.get('model', 'N/A')}")
                print(f"   - usage: {data.get('usage', 'N/A')}")

                if data.get("choices"):
                    content = data["choices"][0].get("message", {}).get("content", "")
                    print(f"\n   Content: {content[:200]}...")

                return True
            else:
                print(f"\n❌ ERROR - Response:")
                try:
                    error_data = response.json()
                    print(json.dumps(error_data, indent=2))
                except:
                    print(response.text)
                return False

    except httpx.TimeoutException:
        print("\n❌ Request timed out after 60 seconds")
        return False
    except Exception as e:
        print(f"\n❌ Exception: {type(e).__name__}: {e}")
        return False


async def test_client_wrapper():
    """Test the PerplexityClient wrapper."""
    from arakis.clients.perplexity import PerplexityClient, PerplexityNotConfiguredError

    print("\n" + "=" * 60)
    print("TESTING PERPLEXITYCLIENT WRAPPER")
    print("=" * 60)

    try:
        # Enable debug mode for detailed output
        client = PerplexityClient(debug=True)

        print(f"\n📋 Client Configuration:")
        print(f"   - API Key configured: {client.is_configured}")
        print(f"   - Model: {client.model}")
        print(f"   - Base URL: {client.BASE_URL}")

        if not client.is_configured:
            print("\n❌ Client not configured (no API key)")
            return False

        # Test research_topic
        print("\n📤 Testing research_topic()...")
        response = await client.research_topic(
            "Effect of aspirin on cardiovascular disease",
            context="Focus on meta-analyses"
        )

        print(f"\n✓ research_topic() succeeded:")
        print(f"   - Content length: {len(response.content)} chars")
        print(f"   - Citations: {len(response.citations)}")
        print(f"   - Search results: {len(response.search_results)}")
        print(f"   - Model: {response.model}")
        print(f"   - Usage: {response.usage}")

        print(f"\n   Content preview: {response.content[:300]}...")

        if response.citations:
            print(f"\n   Citations:")
            for i, c in enumerate(response.citations[:5]):
                print(f"      [{i+1}] {c}")

        if response.search_results:
            print(f"\n   Search Results:")
            for i, sr in enumerate(response.search_results[:3]):
                print(f"      [{i+1}] {sr.title[:50]}...")

        # Test search_for_papers
        print("\n📤 Testing search_for_papers()...")
        papers = await client.search_for_papers(
            "aspirin cardiovascular meta-analysis",
            max_results=3
        )

        print(f"\n✓ search_for_papers() returned {len(papers)} papers:")
        for i, paper in enumerate(papers):
            print(f"\n   Paper {i+1}:")
            print(f"      Title: {paper.title[:60]}...")
            print(f"      Authors: {[str(a) for a in paper.authors[:2]]}...")
            print(f"      Year: {paper.year}")
            print(f"      DOI: {paper.doi}")
            print(f"      ID: {paper.id}")

        # Test get_literature_context
        print("\n📤 Testing get_literature_context()...")
        summary, papers = await client.get_literature_context(
            "Effect of statin therapy on mortality",
            max_papers=3
        )

        print(f"\n✓ get_literature_context() succeeded:")
        print(f"   - Summary length: {len(summary)} chars")
        print(f"   - Papers: {len(papers)}")
        print(f"\n   Summary preview: {summary[:300]}...")

        return True

    except PerplexityNotConfiguredError as e:
        print(f"\n❌ Not configured: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Exception: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all debug tests."""
    print("\n🔍 Starting Perplexity API Debug...\n")

    # Test 1: Raw API
    raw_ok = await test_raw_api()

    # Test 2: Client wrapper (only if raw API works)
    if raw_ok:
        client_ok = await test_client_wrapper()
    else:
        print("\n⏭️  Skipping client wrapper test (raw API failed)")
        client_ok = False

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"   Raw API Test: {'✓ PASSED' if raw_ok else '✗ FAILED'}")
    print(f"   Client Wrapper Test: {'✓ PASSED' if client_ok else '✗ FAILED'}")
    print("=" * 60)

    return raw_ok and client_ok


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
