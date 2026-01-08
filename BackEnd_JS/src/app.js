import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import routes from './routes/index.js';
import { errorHandler } from './middleware/errorHandler.js';
import { requestLogger } from './middleware/logger.js';
import { rateLimiter } from './middleware/rateLimiter.js';

const app = express();

// Security
app.use(helmet());
app.use(cors());

// Parsing
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Middleware
app.use(requestLogger);
app.use(rateLimiter);

// Health check
app.get('/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date() });
});

// Routes
app.use('/api/v1', routes);

// Error handling
app.use(errorHandler);

export default app;