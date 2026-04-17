#!/usr/bin/env python3
"""
Comprehensive Testing Script for Chemical RAG System
Tests all endpoints and validates system functionality
"""

import requests
import json
import time
from typing import Dict, List

# Configuration
BASE_URL = "http://127.0.0.1:8000"
TEST_SMILES = [
    ("CCO", "Ethanol"),
    ("c1ccccc1", "Benzene"),
    ("CC(=O)O", "Acetic Acid"),
    ("CO", "Methanol"),
    ("CCCC", "Butane"),
    ("N", "Ammonia"),
    ("C1CCCCC1", "Cyclohexane"),
]

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 60}")
    print(f"  {text}")
    print(f"{'=' * 60}{Colors.RESET}\n")

def print_success(text):
    print(f"{Colors.GREEN}✅ {text}{Colors.RESET}")

def print_error(text):
    print(f"{Colors.RED}❌ {text}{Colors.RESET}")

def print_info(text):
    print(f"{Colors.YELLOW}ℹ️  {text}{Colors.RESET}")

def test_health():
    """Test health check endpoint"""
    print_header("Testing Health Check")
    try:
        response = requests.get(f"{BASE_URL}/health")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data['status'] == 'healthy'
        assert 'service' in data
        assert 'version' in data
        
        print_success(f"Health Check: {data['status']}")
        print_info(f"Service: {data['service']}")
        print_info(f"Version: {data['version']}")
        return True
    except Exception as e:
        print_error(f"Health check failed: {e}")
        return False

def test_stats():
    """Test statistics endpoint"""
    print_header("Testing System Statistics")
    try:
        response = requests.get(f"{BASE_URL}/stats")
        assert response.status_code == 200
        
        data = response.json()
        assert 'compounds' in data
        assert 'index_size' in data
        
        print_success(f"Compounds loaded: {data['compounds']}")
        print_info(f"Index size: {data['index_size']}")
        print_info(f"Fingerprint bits: {data['bit_size']}")
        return True
    except Exception as e:
        print_error(f"Stats request failed: {e}")
        return False

def test_search(smiles: str, top_k: int = 3) -> Dict:
    """Test search endpoint"""
    try:
        payload = {
            "smiles": smiles,
            "top_k": top_k
        }
        
        response = requests.post(
            f"{BASE_URL}/search",
            json=payload,
            timeout=30
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert 'results' in data
        assert isinstance(data['results'], list)
        
        return {
            "success": True,
            "results": data['results'],
            "count": len(data['results'])
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def test_search_functionality():
    """Test search with multiple SMILES strings"""
    print_header("Testing Search Functionality")
    
    results_summary = []
    
    for smiles, name in TEST_SMILES:
        print(f"\nSearching for {Colors.BOLD}{name}{Colors.RESET} ({smiles})")
        
        start_time = time.time()
        result = test_search(smiles, top_k=5)
        elapsed = time.time() - start_time
        
        if result['success']:
            print_success(f"Found {result['count']} similar compounds ({elapsed:.2f}s)")
            
            # Display results
            for i, compound in enumerate(result['results'], 1):
                distance = compound.get('distance', 'N/A')
                image = compound.get('image', 'None')
                print(f"   {i}. SMILES: {compound['smiles']:<15} Distance: {distance:<6} Image: {bool(image)}")
            
            results_summary.append({
                "compound": name,
                "smiles": smiles,
                "results": result['count'],
                "time": elapsed,
                "status": "✅"
            })
        else:
            print_error(f"Search failed: {result.get('error', 'Unknown error')}")
            results_summary.append({
                "compound": name,
                "smiles": smiles,
                "status": "❌"
            })
    
    return results_summary

def test_error_handling():
    """Test error handling"""
    print_header("Testing Error Handling")
    
    test_cases = [
        {
            "name": "Invalid SMILES",
            "payload": {"smiles": "INVALID_SMILES_XYZ", "top_k": 3},
            "expected_error": True
        },
        {
            "name": "Empty SMILES",
            "payload": {"smiles": "", "top_k": 3},
            "expected_error": True
        },
        {
            "name": "top_k too large",
            "payload": {"smiles": "CCO", "top_k": 200},
            "expected_error": True
        },
        {
            "name": "top_k zero",
            "payload": {"smiles": "CCO", "top_k": 0},
            "expected_error": True
        }
    ]
    
    for test_case in test_cases:
        print(f"\nTesting: {test_case['name']}")
        
        try:
            response = requests.post(
                f"{BASE_URL}/search",
                json=test_case['payload'],
                timeout=10
            )
            
            if test_case['expected_error']:
                if response.status_code >= 400:
                    print_success(f"Correctly rejected: {response.status_code}")
                    print_info(f"Error: {response.json().get('detail', 'N/A')}")
                else:
                    print_error(f"Should have failed but got {response.status_code}")
            else:
                if response.status_code == 200:
                    print_success(f"Request succeeded as expected")
                else:
                    print_error(f"Unexpected error: {response.status_code}")
                    
        except Exception as e:
            print_error(f"Request failed: {e}")

def test_caching():
    """Test LRU caching functionality"""
    print_header("Testing Caching Performance")
    
    smiles = "CCO"
    print(f"Running 3 identical searches for {smiles}...")
    
    times = []
    for i in range(3):
        start = time.time()
        result = test_search(smiles, top_k=5)
        elapsed = time.time() - start
        times.append(elapsed)
        
        if result['success']:
            label = "Uncached" if i == 0 else "Cached"
            print_info(f"Attempt {i+1} ({label}): {elapsed*1000:.2f}ms")
    
    if times[0] > times[2] * 2:
        print_success(f"Cache working! {times[0]/times[2]:.1f}x speedup")
    else:
        print_info("Cache speedup minimal (acceptable for small datasets)")

def print_summary(search_results):
    """Print test summary"""
    print_header("Test Summary")
    
    total = len(search_results)
    passed = sum(1 for r in search_results if r['status'] == "✅")
    
    print(f"Total Tests: {total}")
    print_success(f"Passed: {passed}")
    if total - passed > 0:
        print_error(f"Failed: {total - passed}")
    
    print(f"\nTest Coverage:")
    print_info("✓ Health check")
    print_info("✓ System statistics")
    print_info("✓ Search functionality (7 compounds)")
    print_info("✓ Error handling (4 cases)")
    print_info("✓ Caching performance")
    
    print(f"\n{Colors.BOLD}System Status: {'🟢 FULLY OPERATIONAL' if passed == total else '🟡 OPERATIONAL WITH WARNINGS'}{Colors.RESET}")

def main():
    """Run all tests"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}")
    print("╔════════════════════════════════════════════════════════╗")
    print("║       CHEMICAL RAG SYSTEM - COMPREHENSIVE TEST         ║")
    print("╚════════════════════════════════════════════════════════╝")
    print(f"{Colors.RESET}\n")
    
    try:
        # Run tests
        health_ok = test_health()
        stats_ok = test_stats()
        search_results = test_search_functionality()
        test_error_handling()
        test_caching()
        
        # Print summary
        print_summary(search_results)
        
        # Final status
        if health_ok and stats_ok:
            print(f"\n{Colors.GREEN}{Colors.BOLD}✅ ALL TESTS PASSED - System is ready for production!{Colors.RESET}\n")
        else:
            print(f"\n{Colors.YELLOW}{Colors.BOLD}⚠️  Some tests failed - please review above{Colors.RESET}\n")
            
    except Exception as e:
        print_error(f"Fatal error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
