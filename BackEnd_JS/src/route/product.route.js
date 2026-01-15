import express from 'express';
import { search, getById, compare, getByCategories, getBySearchTerm } from '../controllers/product.controller.js';
import { optionalAuth } from '../middleware/auth.js';
import { validateSearch } from '../validators/product.validator.js';

const router = express.Router();

// Get products by search term (for CategoryProductList)
router.get('/by-term', getBySearchTerm);

// Get products by category IDs (for CategoryProductList)
router.get('/by-categories', getByCategories);

router.get('/search', optionalAuth, validateSearch, search);
router.get('/:id', getById);
router.post('/compare', compare);

export default router;