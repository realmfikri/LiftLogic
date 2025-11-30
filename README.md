# LiftLogic

## Running the live dashboard

1. Start the simulation API (FastAPI + WebSocket):

   ```bash
   PYTHONPATH=src uvicorn server.app:app --reload
   ```

2. Start the React dashboard:

   ```bash
   cd web
   npm install
   npm run dev
   ```

The dashboard renders a 100-floor cross-section, animates ten elevator cars, streams metrics, and exposes controls for passenger bursts, algorithm switching, and taking cars in/out of service.