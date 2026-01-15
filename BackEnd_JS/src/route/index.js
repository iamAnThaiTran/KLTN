import express from 'express';
import authRoutes from './auth.route.js';
import productRoutes from './product.route.js';
import categoryRoutes from './category.route.js';
import crawlerRoutes from './crawler.route.js';

const router = express.Router();

router.use('/auth', authRoutes);
router.use('/categories', categoryRoutes);
router.use('/products', productRoutes);
router.use('/crawlers', crawlerRoutes);

export default router;