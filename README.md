# 🏠 Alloha WhatsApp Bot

AI-powered real estate WhatsApp bot built with FastAPI and deployed on Azure Container Apps.

🚀 **Status**: Ready for production deployment via GitHub Actions!

## 🚀 Features

- ✅ WhatsApp Business API integration
- ✅ AI-powered responses using Abacus.AI
- ✅ PostgreSQL database for conversation history
- ✅ Azure Container Apps deployment
- ✅ Custom domain with SSL (alloha.app)
- ✅ Health monitoring and logging

## 🛠️ Tech Stack

- **Backend**: FastAPI (Python 3.11)
- **AI Provider**: Abacus.AI
- **Database**: PostgreSQL
- **Messaging**: WhatsApp Business API
- **Deployment**: Azure Container Apps
- **CI/CD**: GitHub Actions

## 🏗️ Architecture

```
WhatsApp → Webhook → FastAPI App → AI Service → Database
                         ↓
                   Azure Container Apps
```

## 📦 Deployment

### Automatic Deployment (GitHub Actions)

1. Push to `main` branch triggers automatic deployment
2. Docker image is built and pushed to Docker Hub
3. Azure Container Apps is updated with new image

### Environment Variables

Required secrets in GitHub:
- `DOCKER_USERNAME`
- `DOCKER_PASSWORD`
- `AZURE_CREDENTIALS`
- `WHATSAPP_ACCESS_TOKEN`
- `WHATSAPP_WEBHOOK_VERIFY_TOKEN`
- `WHATSAPP_PHONE_NUMBER_ID`
- `ABACUS_API_KEY`
- `DATABASE_URL`
- `SECRET_KEY`

## 🔧 Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run application
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## 📱 API Endpoints

- `GET /` - Health check and status
- `GET /health` - Detailed health information
- `GET /webhook` - WhatsApp webhook verification
- `POST /webhook` - WhatsApp message handler
- `GET /docs` - API documentation

## 🏠 Production URLs

- **Website**: https://alloha.app
- **API Docs**: https://alloha.app/docs
- **Health Check**: https://alloha.app/health
- **Webhook**: https://alloha.app/webhook

## 📞 WhatsApp Integration

Configure webhook URL in Meta for Developers:
- **Webhook URL**: `https://alloha.app/webhook`
- **Verify Token**: `alloha_secret`

## 🤖 AI Capabilities

The bot can help with:
- Property search and recommendations
- Price inquiries and budget planning
- Location and neighborhood information
- Financing and documentation guidance
- Appointment scheduling

## 🔒 Security

- Non-root container user
- Secure environment variable handling
- HTTPS/SSL encryption
- Input validation and sanitization

## 📊 Monitoring

- Health checks every 30 seconds
- Structured logging
- Error tracking and reporting
- Performance metrics

---

Built with ❤️ for modern real estate experiences
