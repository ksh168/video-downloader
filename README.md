# Video Downloader Service

A Flask-based web service that allows users to download videos using yt-dlp with real-time progress tracking via WebSocket.

## Features

- Web interface for video downloads
- Real-time download progress updates
- API key authentication
- Rate limiting
- Automatic file cleanup
- S3 storage integration
- Docker support

## Prerequisites

- Python 3.11+
- FFmpeg
- yt-dlp
- Docker (optional)
- AWS/S3-compatible storage credentials

## Environment Variables

Create a `.env` file with the following variables:

```
HARDCODED_API_KEY=your_api_key
AWS_ACCESS_KEY_ID=your_aws_key
AWS_SECRET_ACCESS_KEY=your_aws_secret
```

1. Clone the repository:
git clone <repository-url>
cd video-downloader

2. Create and activate virtual environment:

```
python -m venv ./venv
source venv/bin/activate # On Windows: venv\Scripts\activate
```

3. Install dependencies:

```
pip install -r requirements.txt
```

4. Run the application:
```
python app.py
```

### Docker Setup

1. Build the Docker image:
```
docker build -t video-downloader .
```

2. Run the container:
```
docker run -p 3001:3001 video-downloader
```

### Push to Docker Hub

1. Tag the image:
```
docker tag video-downloader <dockerhub-username>/video-downloader:latest
```

2. Push to Docker Hub:
```
docker push <dockerhub-username>/video-downloader:latest
```

## File Cleanup

- Local downloads are automatically cleaned up after successful S3 upload
- S3 files older than 2 hours are automatically deleted
- Local files older than 1 hour are cleaned up via cron job via apscheduler

## Development

The project uses:
- Flask for the web framework
- Flask-SocketIO for real-time progress updates
- yt-dlp for video downloads
- S3 for file storage
- Docker for containerization

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request
