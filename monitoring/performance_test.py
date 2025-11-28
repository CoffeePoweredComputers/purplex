"""
Performance testing script for Purplex
Tests system capacity for 10k concurrent users
"""

import asyncio
import aiohttp
import time
import statistics
import json
from typing import List, Dict, Any
import argparse
from datetime import datetime


class PerformanceTest:
    def __init__(self, base_url: str, num_users: int, duration: int):
        self.base_url = base_url
        self.num_users = num_users
        self.duration = duration
        self.results = {
            'response_times': [],
            'errors': [],
            'success_count': 0,
            'error_count': 0,
            'requests_per_second': 0
        }
    
    async def simulate_user(self, session: aiohttp.ClientSession, user_id: int):
        """Simulate a single user's behavior"""
        endpoints = [
            ('/api/problems/', 'GET', None),
            ('/api/problem-sets/', 'GET', None),
            ('/api/problems/two-sum/', 'GET', None),
            ('/api/submit/', 'POST', {
                'problem_slug': 'two-sum',
                'raw_input': 'This function finds two numbers that add up to target'
            }),
        ]
        
        start_time = time.time()
        while time.time() - start_time < self.duration:
            for endpoint, method, data in endpoints:
                await self.make_request(session, endpoint, method, data, user_id)
                await asyncio.sleep(1)  # Simulate think time
    
    async def make_request(self, session: aiohttp.ClientSession, 
                          endpoint: str, method: str, data: Any, user_id: int):
        """Make a single HTTP request and record metrics"""
        url = self.base_url + endpoint
        start_time = time.time()
        
        try:
            headers = {
                'Authorization': f'Bearer test-token-user-{user_id}',
                'Content-Type': 'application/json'
            }
            
            if method == 'GET':
                async with session.get(url, headers=headers) as response:
                    await response.text()
                    response_time = time.time() - start_time
                    
                    if response.status == 200:
                        self.results['response_times'].append(response_time)
                        self.results['success_count'] += 1
                    else:
                        self.results['errors'].append({
                            'endpoint': endpoint,
                            'status': response.status,
                            'time': datetime.now().isoformat()
                        })
                        self.results['error_count'] += 1
            
            elif method == 'POST':
                async with session.post(url, json=data, headers=headers) as response:
                    await response.text()
                    response_time = time.time() - start_time
                    
                    if response.status in [200, 201]:
                        self.results['response_times'].append(response_time)
                        self.results['success_count'] += 1
                    else:
                        self.results['errors'].append({
                            'endpoint': endpoint,
                            'status': response.status,
                            'time': datetime.now().isoformat()
                        })
                        self.results['error_count'] += 1
                        
        except Exception as e:
            self.results['errors'].append({
                'endpoint': endpoint,
                'error': str(e),
                'time': datetime.now().isoformat()
            })
            self.results['error_count'] += 1
    
    async def run_test(self):
        """Run the performance test with all users"""
        print(f"Starting performance test with {self.num_users} users for {self.duration} seconds")
        
        connector = aiohttp.TCPConnector(limit=0, limit_per_host=0)
        timeout = aiohttp.ClientTimeout(total=30)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            start_time = time.time()
            
            # Create user tasks
            tasks = []
            for i in range(self.num_users):
                task = asyncio.create_task(self.simulate_user(session, i))
                tasks.append(task)
                
                # Ramp up users gradually
                if i % 100 == 0:
                    await asyncio.sleep(0.1)
            
            # Wait for all users to complete
            await asyncio.gather(*tasks)
            
            total_time = time.time() - start_time
            self.results['requests_per_second'] = self.results['success_count'] / total_time
    
    def analyze_results(self):
        """Analyze and display test results"""
        print("\n" + "="*60)
        print("PERFORMANCE TEST RESULTS")
        print("="*60)
        
        total_requests = self.results['success_count'] + self.results['error_count']
        print(f"Total Requests: {total_requests}")
        print(f"Successful Requests: {self.results['success_count']}")
        print(f"Failed Requests: {self.results['error_count']}")
        print(f"Success Rate: {(self.results['success_count'] / total_requests * 100):.2f}%")
        print(f"Requests per Second: {self.results['requests_per_second']:.2f}")
        
        if self.results['response_times']:
            response_times = self.results['response_times']
            print(f"\nResponse Time Statistics:")
            print(f"  Min: {min(response_times)*1000:.2f} ms")
            print(f"  Max: {max(response_times)*1000:.2f} ms")
            print(f"  Mean: {statistics.mean(response_times)*1000:.2f} ms")
            print(f"  Median: {statistics.median(response_times)*1000:.2f} ms")
            print(f"  95th Percentile: {sorted(response_times)[int(len(response_times)*0.95)]*1000:.2f} ms")
            print(f"  99th Percentile: {sorted(response_times)[int(len(response_times)*0.99)]*1000:.2f} ms")
        
        if self.results['errors']:
            print(f"\nError Summary:")
            error_counts = {}
            for error in self.results['errors']:
                key = f"{error.get('endpoint', 'unknown')} - {error.get('status', error.get('error', 'unknown'))}"
                error_counts[key] = error_counts.get(key, 0) + 1
            
            for error_type, count in sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
                print(f"  {error_type}: {count}")
        
        # Check if system can handle 10k users
        print("\n" + "="*60)
        if self.results['error_count'] / total_requests > 0.01:  # More than 1% errors
            print("❌ FAIL: Error rate too high for 10k users")
        elif statistics.mean(self.results['response_times']) > 1.0:  # Mean response time > 1 second
            print("❌ FAIL: Response time too high for 10k users")
        else:
            print("✅ PASS: System can handle the load!")
        
        # Save detailed results
        with open('performance_test_results.json', 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"\nDetailed results saved to performance_test_results.json")


async def main():
    parser = argparse.ArgumentParser(description='Performance test for Purplex')
    parser.add_argument('--url', default='http://localhost:8000', help='Base URL of Purplex')
    parser.add_argument('--users', type=int, default=100, help='Number of concurrent users')
    parser.add_argument('--duration', type=int, default=60, help='Test duration in seconds')
    
    args = parser.parse_args()
    
    test = PerformanceTest(args.url, args.users, args.duration)
    await test.run_test()
    test.analyze_results()


if __name__ == '__main__':
    asyncio.run(main())