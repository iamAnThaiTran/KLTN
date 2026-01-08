export const validateSearch = (req, res, next) => {
  const { q, category, minPrice, maxPrice } = req.query;

  if (q && typeof q !== 'string') {
    return res.status(400).json({
      success: false,
      error: { message: 'Search query must be a string' },
    });
  }

  if (minPrice && isNaN(parseFloat(minPrice))) {
    return res.status(400).json({
      success: false,
      error: { message: 'minPrice must be a number' },
    });
  }

  if (maxPrice && isNaN(parseFloat(maxPrice))) {
    return res.status(400).json({
      success: false,
      error: { message: 'maxPrice must be a number' },
    });
  }

  next();
};
