"""
Production Subagent UI/UX Testers
==================================

Ship Ship Ship Philosophy: Test in production with real agents.

These subagents continuously test the live application like real users,
finding bugs and UX issues before actual users encounter them.

Each agent has a persona and testing workflow that mirrors real usage patterns.
"""

import asyncio
import httpx
from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel
import json

class TestIssue(BaseModel):
    """An issue found during production testing"""
    severity: str  # 'critical', 'high', 'medium', 'low'
    category: str  # 'bug', 'ux', 'performance', 'security'
    description: str
    example: Optional[str] = None
    endpoint: Optional[str] = None
    screenshot_url: Optional[str] = None
    timestamp: datetime


class TestSuggestion(BaseModel):
    """Improvement suggestion from testing"""
    category: str  # 'ux', 'performance', 'feature'
    description: str
    priority: str  # 'high', 'medium', 'low'
    example: Optional[str] = None


class TestResult(BaseModel):
    """Result from a production test run"""
    flow_name: str
    persona: str
    success: bool
    duration_seconds: float
    timestamp: datetime
    issues: List[TestIssue] = []
    suggestions: List[TestSuggestion] = []
    metrics: Dict[str, Any] = {}


class ProductionUITester:
    """
    Base class for production UI/UX testing agents.
    
    Each subagent tests specific flows from a user persona perspective.
    Runs continuously in production to catch issues early.
    """
    
    def __init__(self, base_url: str = "https://web-production-a6ccf.up.railway.app"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
        
    async def test_flow(self, flow_name: str, persona: str) -> TestResult:
        """Run a complete test flow and return results"""
        start_time = datetime.utcnow()
        result = TestResult(
            flow_name=flow_name,
            persona=persona,
            success=True,
            duration_seconds=0.0,
            timestamp=start_time,
            issues=[],
            suggestions=[]
        )
        
        try:
            # Subclasses implement specific flows
            await self._execute_flow(flow_name, persona, result)
            
        except Exception as e:
            result.success = False
            result.issues.append(TestIssue(
                severity='critical',
                category='bug',
                description=f"Test flow crashed: {str(e)}",
                endpoint=flow_name,
                timestamp=datetime.utcnow()
            ))
        
        finally:
            end_time = datetime.utcnow()
            result.duration_seconds = (end_time - start_time).total_seconds()
            
        return result
    
    async def _execute_flow(self, flow_name: str, persona: str, result: TestResult):
        """Override in subclasses to implement specific flows"""
        raise NotImplementedError


class PestiAgentTester(ProductionUITester):
    """
    Tests Pesti (sales agent) functionality.
    
    Persona: Sales rep using Pesti to automate outreach
    Tests: Voice training, response quality, personality consistency
    """
    
    async def _execute_flow(self, flow_name: str, persona: str, result: TestResult):
        if flow_name == "voice_training_youtube":
            await self._test_voice_training_youtube(result)
        elif flow_name == "voice_training_drive":
            await self._test_voice_training_drive(result)
        elif flow_name == "pesti_response_quality":
            await self._test_pesti_response_quality(result)
        elif flow_name == "pesti_personality":
            await self._test_pesti_personality(result)
    
    async def _test_voice_training_youtube(self, result: TestResult):
        """Test YouTube video ingestion for voice training"""
        
        # 1. Test UI loads
        response = await self.client.get(f"{self.base_url}/voice-training.html")
        if response.status_code != 200:
            result.issues.append(TestIssue(
                severity='high',
                category='bug',
                description="Voice training UI failed to load",
                endpoint="/voice-training.html",
                timestamp=datetime.utcnow()
            ))
            result.success = False
            return
        
        # 2. Test YouTube extraction API
        test_youtube_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        payload = {
            "source_type": "youtube",
            "source_url": test_youtube_url,
            "user_id": "production-tester-pesti"
        }
        
        response = await self.client.post(
            f"{self.base_url}/api/voice/training/ingest/url",
            json=payload
        )
        
        if response.status_code == 200:
            data = response.json()
            result.metrics['youtube_extraction_success'] = True
            result.metrics['youtube_extraction_time'] = data.get('processing_time', 0)
            
            # Check response quality
            if 'sample_id' not in data:
                result.suggestions.append(TestSuggestion(
                    category='ux',
                    description="Response should include sample_id for tracking",
                    priority='medium'
                ))
        else:
            result.issues.append(TestIssue(
                severity='high',
                category='bug',
                description=f"YouTube extraction failed with status {response.status_code}",
                endpoint="/api/voice/training/ingest/url",
                example=response.text[:200],
                timestamp=datetime.utcnow()
            ))
            result.success = False
    
    async def _test_voice_training_drive(self, result: TestResult):
        """Test Google Drive document ingestion"""
        
        # Test Drive extraction API
        test_drive_url = "https://docs.google.com/document/d/test/edit"
        payload = {
            "source_type": "drive",
            "source_url": test_drive_url,
            "user_id": "production-tester-pesti"
        }
        
        response = await self.client.post(
            f"{self.base_url}/api/voice/training/ingest/url",
            json=payload
        )
        
        # Expect 401 or 400 (no OAuth token for test user)
        # We're testing the endpoint responds appropriately
        if response.status_code in [401, 400]:
            result.metrics['drive_auth_check'] = 'working'
            error_data = response.json()
            
            if 'detail' in error_data and 'oauth' in error_data['detail'].lower():
                # Good - proper error message
                pass
            else:
                result.suggestions.append(TestSuggestion(
                    category='ux',
                    description="Drive auth error should mention OAuth/Google connection",
                    priority='low',
                    example=error_data.get('detail', '')
                ))
        else:
            result.issues.append(TestIssue(
                severity='medium',
                category='bug',
                description=f"Drive endpoint returned unexpected status {response.status_code}",
                endpoint="/api/voice/training/ingest/url",
                timestamp=datetime.utcnow()
            ))
    
    async def _test_pesti_response_quality(self, result: TestResult):
        """Test Pesti response generation quality"""
        
        # This would test actual Pesti agent endpoint
        # For now, placeholder showing the pattern
        
        test_prompts = [
            "Tell me about your pricing",
            "I'm not interested",
            "Can you send me more information?",
            "What makes you different from competitors?"
        ]
        
        for prompt in test_prompts:
            # Would call Pesti endpoint here
            # Check for natural language, personality consistency, etc.
            pass
        
        result.suggestions.append(TestSuggestion(
            category='feature',
            description="Add Pesti response quality testing endpoint",
            priority='high',
            example="POST /api/agents/pesti/test-response"
        ))
    
    async def _test_pesti_personality(self, result: TestResult):
        """Test Pesti personality consistency across conversations"""
        
        result.suggestions.append(TestSuggestion(
            category='feature',
            description="Implement personality variant A/B testing",
            priority='high',
            example="Test professional vs casual vs consultative tones"
        ))


class JarvisAgentTester(ProductionUITester):
    """
    Tests Jarvis (multi-purpose assistant) functionality.
    
    Persona: User connecting apps and using Jarvis for automation
    Tests: Integration connections, data sync, command execution
    """
    
    async def _execute_flow(self, flow_name: str, persona: str, result: TestResult):
        if flow_name == "integrations_marketplace":
            await self._test_integrations_marketplace(result)
        elif flow_name == "oauth_connection":
            await self._test_oauth_connection(result)
        elif flow_name == "jarvis_command":
            await self._test_jarvis_command(result)
    
    async def _test_integrations_marketplace(self, result: TestResult):
        """Test integration marketplace UI (when built)"""
        
        # Check if integrations page exists
        response = await self.client.get(f"{self.base_url}/integrations.html")
        
        if response.status_code == 404:
            result.suggestions.append(TestSuggestion(
                category='feature',
                description="Create integrations marketplace UI",
                priority='high',
                example="Show available apps: Google, HubSpot, Slack, YardFlow"
            ))
        elif response.status_code == 200:
            # Page exists - test it loads properly
            result.metrics['integrations_ui_loaded'] = True
            
            # Check for key elements (would use actual HTML parsing)
            if 'google' not in response.text.lower():
                result.suggestions.append(TestSuggestion(
                    category='ux',
                    description="Integrations page should show Google integration",
                    priority='medium'
                ))
    
    async def _test_oauth_connection(self, result: TestResult):
        """Test OAuth connection flow"""
        
        # Test Google OAuth authorize endpoint
        response = await self.client.get(
            f"{self.base_url}/api/auth/google/authorize",
            follow_redirects=False
        )
        
        if response.status_code in [302, 307]:
            # Redirect to Google - good
            result.metrics['oauth_redirect'] = 'working'
            
            # Check redirect URL
            location = response.headers.get('location', '')
            if 'accounts.google.com' not in location:
                result.issues.append(TestIssue(
                    severity='high',
                    category='bug',
                    description="OAuth redirect not pointing to Google",
                    endpoint="/api/auth/google/authorize",
                    example=location[:100],
                    timestamp=datetime.utcnow()
                ))
        else:
            result.issues.append(TestIssue(
                severity='high',
                category='bug',
                description=f"OAuth authorize returned {response.status_code}",
                endpoint="/api/auth/google/authorize",
                timestamp=datetime.utcnow()
            ))
    
    async def _test_jarvis_command(self, result: TestResult):
        """Test Jarvis command execution (when implemented)"""
        
        result.suggestions.append(TestSuggestion(
            category='feature',
            description="Create Jarvis command API endpoint",
            priority='high',
            example="POST /api/agents/jarvis/execute with action commands"
        ))


class AnalyticsDashboardTester(ProductionUITester):
    """
    Tests analytics and dashboard functionality.
    
    Persona: Manager checking team performance metrics
    Tests: Dashboard loads, metrics accuracy, chart rendering
    """
    
    async def _execute_flow(self, flow_name: str, persona: str, result: TestResult):
        if flow_name == "analytics_dashboard":
            await self._test_analytics_dashboard(result)
        elif flow_name == "analytics_metrics":
            await self._test_analytics_metrics(result)
        elif flow_name == "recovery_system":
            await self._test_recovery_system(result)
    
    async def _test_analytics_dashboard(self, result: TestResult):
        """Test analytics dashboard endpoint"""
        
        response = await self.client.get(
            f"{self.base_url}/api/analytics/dashboard?time_window=day"
        )
        
        if response.status_code == 200:
            data = response.json()
            result.metrics['dashboard_loaded'] = True
            
            # Check for expected fields
            expected_fields = ['workflows', 'performance', 'quality', 'time_window']
            missing_fields = [f for f in expected_fields if f not in data]
            
            if missing_fields:
                result.issues.append(TestIssue(
                    severity='medium',
                    category='bug',
                    description=f"Dashboard missing fields: {', '.join(missing_fields)}",
                    endpoint="/api/analytics/dashboard",
                    timestamp=datetime.utcnow()
                ))
            
            # Check if nulls (expected if no data)
            if data.get('workflows', {}).get('total') is None:
                result.metrics['no_workflow_data'] = True
                result.suggestions.append(TestSuggestion(
                    category='ux',
                    description="Create sample workflow data for testing",
                    priority='medium',
                    example="Seed database with 10-20 test workflows"
                ))
        
        elif response.status_code == 500:
            # Server error - check if it's the enum issue
            error_data = response.json()
            if 'enum' in error_data.get('detail', '').lower():
                result.issues.append(TestIssue(
                    severity='critical',
                    category='bug',
                    description="PostgreSQL enum compatibility error still present",
                    endpoint="/api/analytics/dashboard",
                    example=error_data.get('detail', '')[:200],
                    timestamp=datetime.utcnow()
                ))
                result.success = False
            else:
                result.issues.append(TestIssue(
                    severity='high',
                    category='bug',
                    description="Dashboard returned 500 error",
                    endpoint="/api/analytics/dashboard",
                    example=error_data.get('detail', '')[:200],
                    timestamp=datetime.utcnow()
                ))
                result.success = False
    
    async def _test_analytics_metrics(self, result: TestResult):
        """Test analytics metrics endpoint"""
        
        response = await self.client.get(
            f"{self.base_url}/api/analytics/metrics?time_window=week"
        )
        
        if response.status_code == 200:
            data = response.json()
            result.metrics['metrics_endpoint'] = 'working'
            
            # Performance check
            if result.duration_seconds > 2.0:
                result.suggestions.append(TestSuggestion(
                    category='performance',
                    description="Metrics endpoint slow (>2s), consider caching",
                    priority='medium',
                    example=f"Current: {result.duration_seconds:.2f}s"
                ))
        elif response.status_code == 500:
            result.issues.append(TestIssue(
                severity='high',
                category='bug',
                description="Metrics endpoint returned 500 error",
                endpoint="/api/analytics/metrics",
                timestamp=datetime.utcnow()
            ))
    
    async def _test_recovery_system(self, result: TestResult):
        """Test workflow recovery system"""
        
        response = await self.client.get(
            f"{self.base_url}/api/analytics/recovery/stats"
        )
        
        if response.status_code == 200:
            data = response.json()
            result.metrics['recovery_stats'] = 'working'
            
            # Check recovery metrics
            if data.get('stuck_workflows') is None:
                result.metrics['no_stuck_workflows'] = True
        elif response.status_code == 500:
            result.issues.append(TestIssue(
                severity='high',
                category='bug',
                description="Recovery stats endpoint failing",
                endpoint="/api/analytics/recovery/stats",
                timestamp=datetime.utcnow()
            ))


class ProductionTestRunner:
    """
    Orchestrates all production testing agents.
    
    Runs continuously, rotating through different test flows.
    Reports issues and suggestions for rapid iteration.
    """
    
    def __init__(self):
        self.testers = {
            'pesti': PestiAgentTester(),
            'jarvis': JarvisAgentTester(),
            'analytics': AnalyticsDashboardTester()
        }
        
    async def run_all_tests(self) -> List[TestResult]:
        """Run all test flows across all agents"""
        
        results = []
        
        # Pesti tests
        pesti = self.testers['pesti']
        results.append(await pesti.test_flow("voice_training_youtube", "sales_rep"))
        results.append(await pesti.test_flow("voice_training_drive", "sales_rep"))
        results.append(await pesti.test_flow("pesti_personality", "sales_rep"))
        
        # Jarvis tests
        jarvis = self.testers['jarvis']
        results.append(await jarvis.test_flow("integrations_marketplace", "business_user"))
        results.append(await jarvis.test_flow("oauth_connection", "business_user"))
        results.append(await jarvis.test_flow("jarvis_command", "business_user"))
        
        # Analytics tests
        analytics = self.testers['analytics']
        results.append(await analytics.test_flow("analytics_dashboard", "manager"))
        results.append(await analytics.test_flow("analytics_metrics", "manager"))
        results.append(await analytics.test_flow("recovery_system", "ops_engineer"))
        
        return results
    
    async def run_smoke_test(self) -> TestResult:
        """Quick smoke test of critical functionality"""
        
        result = TestResult(
            flow_name="smoke_test",
            persona="automated_tester",
            success=True,
            duration_seconds=0.0,
            timestamp=datetime.utcnow()
        )
        
        start = datetime.utcnow()
        client = httpx.AsyncClient(timeout=10.0)
        base_url = "https://web-production-a6ccf.up.railway.app"
        
        try:
            # 1. Health check
            resp = await client.get(f"{base_url}/health")
            if resp.status_code != 200:
                result.success = False
                result.issues.append(TestIssue(
                    severity='critical',
                    category='bug',
                    description="Health check failed",
                    endpoint="/health",
                    timestamp=datetime.utcnow()
                ))
            
            # 2. OAuth endpoint
            resp = await client.get(f"{base_url}/api/auth/google/authorize", follow_redirects=False)
            if resp.status_code not in [302, 307]:
                result.issues.append(TestIssue(
                    severity='high',
                    category='bug',
                    description="OAuth not redirecting",
                    endpoint="/api/auth/google/authorize",
                    timestamp=datetime.utcnow()
                ))
            
            # 3. Analytics dashboard
            resp = await client.get(f"{base_url}/api/analytics/dashboard?time_window=day")
            if resp.status_code == 500:
                error = resp.json()
                if 'enum' in error.get('detail', '').lower():
                    result.success = False
                    result.issues.append(TestIssue(
                        severity='critical',
                        category='bug',
                        description="Enum compatibility bug still present",
                        endpoint="/api/analytics/dashboard",
                        timestamp=datetime.utcnow()
                    ))
            
            # 4. Database check
            resp = await client.get(f"{base_url}/api/debug/db-tables")
            if resp.status_code == 200:
                data = resp.json()
                result.metrics['database_tables'] = data.get('table_count', 0)
            
        except Exception as e:
            result.success = False
            result.issues.append(TestIssue(
                severity='critical',
                category='bug',
                description=f"Smoke test crashed: {str(e)}",
                timestamp=datetime.utcnow()
            ))
        
        finally:
            await client.aclose()
            end = datetime.utcnow()
            result.duration_seconds = (end - start).total_seconds()
        
        return result
    
    def format_report(self, results: List[TestResult]) -> str:
        """Format test results into readable report"""
        
        report_lines = [
            "🚢 Production Testing Report 🚢",
            "=" * 50,
            f"Timestamp: {datetime.utcnow().isoformat()}",
            ""
        ]
        
        total_tests = len(results)
        passed_tests = sum(1 for r in results if r.success)
        failed_tests = total_tests - passed_tests
        
        total_issues = sum(len(r.issues) for r in results)
        total_suggestions = sum(len(r.suggestions) for r in results)
        
        report_lines.extend([
            f"Tests Run: {total_tests}",
            f"✅ Passed: {passed_tests}",
            f"❌ Failed: {failed_tests}",
            f"🐛 Issues Found: {total_issues}",
            f"💡 Suggestions: {total_suggestions}",
            ""
        ])
        
        # Group issues by severity
        critical_issues = []
        high_issues = []
        
        for result in results:
            for issue in result.issues:
                if issue.severity == 'critical':
                    critical_issues.append((result.flow_name, issue))
                elif issue.severity == 'high':
                    high_issues.append((result.flow_name, issue))
        
        if critical_issues:
            report_lines.append("🚨 CRITICAL ISSUES:")
            for flow, issue in critical_issues:
                report_lines.append(f"  [{flow}] {issue.description}")
                if issue.endpoint:
                    report_lines.append(f"    Endpoint: {issue.endpoint}")
            report_lines.append("")
        
        if high_issues:
            report_lines.append("⚠️  HIGH PRIORITY ISSUES:")
            for flow, issue in high_issues:
                report_lines.append(f"  [{flow}] {issue.description}")
            report_lines.append("")
        
        # Top suggestions
        if total_suggestions > 0:
            report_lines.append("💡 TOP SUGGESTIONS:")
            high_priority_suggestions = []
            for result in results:
                for suggestion in result.suggestions:
                    if suggestion.priority == 'high':
                        high_priority_suggestions.append((result.flow_name, suggestion))
            
            for flow, suggestion in high_priority_suggestions[:5]:
                report_lines.append(f"  [{flow}] {suggestion.description}")
            report_lines.append("")
        
        return "\n".join(report_lines)


# CLI interface for manual testing
async def main():
    """Run production tests and print report"""
    
    runner = ProductionTestRunner()
    
    print("🚢 Running production smoke test...")
    smoke_result = await runner.run_smoke_test()
    
    if smoke_result.success:
        print("✅ Smoke test PASSED")
        print("\n🚢 Running comprehensive test suite...")
        results = await runner.run_all_tests()
        results.insert(0, smoke_result)
    else:
        print("❌ Smoke test FAILED - critical issues found")
        results = [smoke_result]
    
    # Print report
    report = runner.format_report(results)
    print("\n" + report)
    
    # Save to file
    with open('/tmp/production_test_report.txt', 'w') as f:
        f.write(report)
        f.write("\n\n" + "=" * 50 + "\n")
        f.write("DETAILED RESULTS:\n")
        f.write(json.dumps([r.dict() for r in results], indent=2, default=str))
    
    print("\n📄 Full report saved to: /tmp/production_test_report.txt")
    
    # Return exit code based on critical issues
    has_critical = any(
        any(issue.severity == 'critical' for issue in r.issues)
        for r in results
    )
    
    return 1 if has_critical else 0


if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
