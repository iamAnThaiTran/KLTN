import express from 'express';
import authRoutes from './auth.routes.js';
import productRoutes from './product.routes.js';
import favoriteRoutes from './favorite.routes.js';
import historyRoutes from './history.routes.js';
import alertRoutes from './alert.routes.js';
import adminRoutes from './admin.routes.js';

const router = express.Router();

router.use('/auth', authRoutes);
router.use('/products', productRoutes);
router.use('/favorites', favoriteRoutes);
router.use('/history', historyRoutes);
router.use('/alerts', alertRoutes);
router.use('/admin', adminRoutes);

export default router;