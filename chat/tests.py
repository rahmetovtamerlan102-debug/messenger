import pytest
from django.test import Client
from django.contrib.auth.models import User
from channels.testing import WebsocketCommunicator
from .consumers import ChatConsumer
from .models import Chat

@pytest.mark.django_db
def test_register():
    client = Client()
    response = client.post('/api/register/', {'username': 'test', 'password': 'testpass123'})
    assert response.status_code == 201
    assert User.objects.filter(username='test').exists()

@pytest.mark.django_db
def test_login():
    User.objects.create_user(username='test', password='testpass123')
    client = Client()
    response = client.post('/api/login/', {'username': 'test', 'password': 'testpass123'}, content_type='application/json')
    assert response.status_code == 200
    assert 'access' in response.json()
