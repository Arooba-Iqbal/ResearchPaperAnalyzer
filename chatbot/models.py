"""
Models for the chatbot app.
"""
from django.db import models
from django.contrib.auth.models import User
from papers.models import Paper
import uuid



class Conversation(models.Model):
    """Model representing a conversation session."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    paper = models.ForeignKey(Paper, on_delete=models.CASCADE, related_name='conversations')
    session_id = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"Conversation {self.id} for {self.paper.title}"


class Message(models.Model):
    """Model representing a message in a conversation."""
    MESSAGE_TYPES = [
        ('user', 'User Message'),
        ('assistant', 'Assistant Response'),
        ('system', 'System Message'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPES)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # RAG-specific fields
    relevant_chunks = models.JSONField(blank=True, null=True)  # Store relevant paper chunks
    confidence_score = models.FloatField(blank=True, null=True)
    sources = models.JSONField(blank=True, null=True)  # Store source information
    
    class Meta:
        ordering = ['timestamp']
    
    def __str__(self):
        return f"{self.message_type} message in {self.conversation.id}"


class RAGQuery(models.Model):
    """Model representing a RAG query and its results."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='rag_queries')
    query = models.TextField()
    response = models.TextField()
    relevant_chunks = models.JSONField()  # Store chunk IDs and content
    embedding_query = models.BinaryField(blank=True, null=True)
    similarity_scores = models.JSONField()  # Store similarity scores
    processing_time = models.FloatField(blank=True, null=True)  # Time taken to process
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"RAG Query: {self.query[:50]}..."


class PaperHighlight(models.Model):
    """Model representing highlights on papers based on chatbot responses."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    paper = models.ForeignKey(Paper, on_delete=models.CASCADE, related_name='highlights')
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='highlights')
    text_content = models.TextField()  # The highlighted text
    page_number = models.IntegerField(blank=True, null=True)
    start_position = models.IntegerField(blank=True, null=True)
    end_position = models.IntegerField(blank=True, null=True)
    highlight_type = models.CharField(
        max_length=20,
        choices=[
            ('question', 'Question'),
            ('answer', 'Answer'),
            ('relevant', 'Relevant Content'),
            ('citation', 'Citation'),
        ],
        default='relevant'
    )
    color = models.CharField(max_length=7, default='#FFD700')  # Hex color
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"Highlight: {self.text_content[:50]}... on {self.paper.title}"


