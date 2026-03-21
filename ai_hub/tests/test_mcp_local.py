from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from ai_hub.models import MCPServer
import json

User = get_user_model()

class MCPServerScanAndCreateTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.admin = User.objects.create_superuser(username='admin', password='adminpassword')
        self.client = Client()

    def test_create_mcp_server_form_fields(self):
        """Test form fields in the creation page"""
        self.client.login(username='admin', password='adminpassword')
        response = self.client.get(reverse('create_mcp_server'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name')
        self.assertContains(response, 'device_id')
        self.assertContains(response, 'domain')
        # Ensure removed fields are not present
        self.assertNotContains(response, 'builtin_kind')
        self.assertNotContains(response, 'server_type')

    def test_create_mcp_server_local_detection(self):
        """Test if localhost URL is automatically detected as local server"""
        self.client.login(username='testuser', password='password123')
        data = {
            'name': 'My Local Server',
            'device_id': 'local-001',
            'domain': 'http://localhost:8001',
            'description': 'A local test server',
            'location': 'Localhost',
            'is_active': True
        }
        response = self.client.post(reverse('create_mcp_server'), data)
        self.assertEqual(response.status_code, 302) # Redirect to dashboard
        
        server = MCPServer.objects.get(device_id='local-001')
        self.assertEqual(server.server_type, 'local')
        self.assertTrue(server.is_local_managed)
        self.assertEqual(server.owner, self.user)

    def test_create_mcp_server_remote_url(self):
        """Test if remote URL is kept as private server"""
        self.client.login(username='testuser', password='password123')
        data = {
            'name': 'My Remote Server',
            'device_id': 'remote-001',
            'domain': 'https://mcp.example.com',
            'description': 'A remote test server',
            'location': 'Cloud',
            'is_active': True
        }
        response = self.client.post(reverse('create_mcp_server'), data)
        self.assertEqual(response.status_code, 302)
        
        server = MCPServer.objects.get(device_id='remote-001')
        self.assertEqual(server.server_type, 'private')
        self.assertFalse(server.is_local_managed)
        self.assertEqual(server.owner, self.user)

    def test_dashboard_auto_scan_call(self):
        """Test if dashboard access doesn't crash and returns 200 (admin)"""
        self.client.login(username='admin', password='adminpassword')
        response = self.client.get(reverse('mcp_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'local_servers')
