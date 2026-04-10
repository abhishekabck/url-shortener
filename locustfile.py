from locust import HttpUser, task, between

class URLShortenerUser(HttpUser):
    wait_time = between(1, 2)
    short_code = None
    
    def on_start(self):
        # create a short URL first
        response = self.client.post("/shorten", json={
            "original_url": "https://google.com"
        })
        if response.status_code == 201:
            self.short_code = response.json()["short_code"]
    
    @task(10)
    def redirect(self):
        if self.short_code:
            self.client.get(f"/{self.short_code}",
                            allow_redirects=False)
    
    @task(3)
    def stats(self):
        if self.short_code:
            self.client.get(f"/{self.short_code}/stats")
        
    @task(1)
    def shorten(self):
        self.client.post("/shorten", json={
            "original_url": "https://example.com"
        })