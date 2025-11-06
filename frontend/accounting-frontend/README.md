# Fernando Frontend

React + TypeScript frontend for automated document processing.

## Features

- User authentication and registration
- Document upload with drag-and-drop
- Job tracking dashboard
- Manual review interface (in development)
- Admin dashboard (in development)
- Responsive design with Tailwind CSS

## Setup

1. Install dependencies:
```bash
pnpm install
```

2. Start development server:
```bash
pnpm run dev
```

The application will be available at `http://localhost:5173`

## Backend Connection

The frontend connects to the FastAPI backend at `http://localhost:8000`.

Make sure the backend is running before starting the frontend.

## Building for Production

```bash
pnpm run build
```

The production build will be in the `dist` directory.

## Technologies

- React 18
- TypeScript
- Tailwind CSS
- React Router
- Axios for API calls
- Lucide React for icons
- Shadcn/ui components
