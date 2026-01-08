import express from 'express';
import { search, getById, compare } from '../controllers/product.controller.js';
import { optionalAuth } from '../middleware/auth.js';
import { validateSearch } from '../validators/product.validator.js';

const router = express.Router();

router.get('/search', optionalAuth, validateSearch, search);
router.get('/:id', getById);
router.post('/compare', compare);

export default router;