import express from 'express';
import { getCategories, getCategoryById } from '../controllers/category.controller.js';

const router = express.Router();

// Get categories with filtering
router.get('/', getCategories);

// Get category by ID with subcategories
router.get('/:id', getCategoryById);

export default router;
