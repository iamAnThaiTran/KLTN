import express from 'express';
import authRoutes from './auth.route.js';
import productRoutes from './product.route.js';

const router = express.Router();

router.use('/auth', authRoutes);
router.use('/products', productRoutes);

export default router;