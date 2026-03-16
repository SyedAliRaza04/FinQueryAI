from rest_framework import serializers
from .models import ChatSession, ChatMessage

class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ['id', 'role', 'content', 'cards_json', 'code_snippet', 'raw_data_json', 'created_at']

class ChatSessionSerializer(serializers.ModelSerializer):
    messages = ChatMessageSerializer(many=True, read_only=True)
    owner = serializers.ReadOnlyField(source='owner.username')
    
    class Meta:
        model = ChatSession
        fields = ['id', 'owner', 'title', 'messages', 'created_at', 'updated_at']

class ChatSessionListSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source='owner.username')

    class Meta:
        model = ChatSession
        fields = ['id', 'owner', 'title', 'updated_at']
