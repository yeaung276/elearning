import whisper

from celery import shared_task
from .models import VideoMaterial


@shared_task
def transcribe(video_id):
    video = VideoMaterial.objects.get(id=video_id)
    
    model = whisper.load_model("base")
    result = model.transcribe(video.path.path)
    
    video.transcript = result["text"][:255]
    video.save()
    
    return result["text"]
