from django.db import models

class Company(models.Model):
    name = models.CharField(max_length=255)
    website = models.URLField(blank=True, null=True)

    def __str__(self):
        return self.name

class SourceType(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name

class Source(models.Model):
    name = models.CharField(max_length=255)
    type = models.ForeignKey(SourceType, on_delete=models.CASCADE, related_name="sources")
    url = models.URLField()

    def __str__(self):
        return f"{self.name} ({self.type.name})"

class Mention(models.Model):
    SENTIMENT_CHOICES = [
        ("positive", "Positive"),
        ("negative", "Negative"),
        ("neutral", "Neutral"),
    ]
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="mentions")
    source = models.ForeignKey(Source, on_delete=models.CASCADE, related_name="mentions")
    title = models.CharField(max_length=255)
    content = models.TextField()
    original_url = models.URLField()
    published_at = models.DateTimeField()
    sentiment_label = models.CharField(max_length=20, choices=SENTIMENT_CHOICES)
    sentiment_score = models.FloatField(null=True, blank=True)
    is_urgent = models.BooleanField(default=False)
    urgency_reason = models.TextField(blank=True, null=True)
    raw_metadata = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-published_at"]

    def __str__(self):
        return self.title
