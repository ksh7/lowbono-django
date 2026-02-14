from django.core.files.storage import Storage
from django.core.files import File
from django.conf import settings

import supabase
import requests

class SupabaseCustomStorage(Storage):
    def __init__(self):
        self.client = supabase.create_client(settings.SUPABASE_INSTANCE_URL, settings.SUPABASE_STORAGE_KEY)
        self.bucket_name = settings.SUPABASE_STORAGE_BUCKET

    def _open(self, name, mode='rb'):
        raise NotImplementedError("This method is not implemented.")

    def _save(self, name, content):
        content.seek(0)
        response = self.client.storage.from_(self.bucket_name).upload(name, content.read())
        return name

    def delete(self, name):
        response = self.client.storage.from_(self.bucket_name).remove(name)
        return name

    def exists(self, name):
        response = requests.head(self.url(name))
        return response.status_code == 200

    def url(self, name):
        return self.client.storage.from_(self.bucket_name).get_public_url(name)
