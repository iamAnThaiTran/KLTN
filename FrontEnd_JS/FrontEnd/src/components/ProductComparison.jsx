import React, { useState } from 'react';
import { Loader, X } from 'lucide-react';
import ProductSelector from './ProductSelector';
import ComparisonResult from './ComparisonResult';
import { compareProducts } from '../utils/comparisonApi';

/**
 * ProductComparison Component
 * Main orchestrator for product comparison workflow
 * Manages state and transitions between selector and result views
 */
export default function ProductComparison({ onClose }) {
  const [step, setStep] = useState('select'); // 'select' | 'loading' | 'result'
  const [comparisonData, setComparisonData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleProductsSelected = async (productIds, question) => {
    try {
      setLoading(true);
      setError(null);
      setStep('loading');

      console.log('📊 Comparing products:', productIds, 'Question:', question);

      // Call the comparison API
      const result = await compareProducts(productIds, question);

      console.log('✅ Comparison result:', result);

      setComparisonData(result);
      setStep('result');
    } catch (err) {
      console.error('❌ Error comparing products:', err);
      setError(err.message || 'Failed to compare products. Please try again.');
      setStep('select');
    } finally {
      setLoading(false);
    }
  };

  const handleBack = () => {
    if (step === 'result') {
      setStep('select');
      setComparisonData(null);
      setError(null);
    } else {
      onClose();
    }
  };

  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      background: 'rgba(0, 0, 0, 0.5)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000,
      padding: '20px',
      backdropFilter: 'blur(4px)',
    }}>
      {/* Close button */}
      <button
        onClick={onClose}
        style={{
          position: 'fixed',
          top: '20px',
          right: '20px',
          background: '#fff',
          border: 'none',
          borderRadius: '50%',
          width: '40px',
          height: '40px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          cursor: 'pointer',
          zIndex: 1001,
          boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
          transition: 'all 0.2s',
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.background = '#f3f4f6';
          e.currentTarget.style.transform = 'scale(1.1)';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.background = '#fff';
          e.currentTarget.style.transform = 'scale(1)';
        }}
      >
        <X size={20} color="#6b7280" />
      </button>

      {/* Main container */}
      <div style={{
        width: '100%',
        maxWidth: step === 'loading' ? '400px' : '900px',
        maxHeight: '90vh',
        background: '#fff',
        borderRadius: '20px',
        overflow: 'hidden',
        boxShadow: '0 20px 60px rgba(0, 0, 0, 0.3)',
        display: 'flex',
        flexDirection: 'column',
        animation: 'slideIn 0.3s ease',
      }}>
        <style>{`
          @keyframes slideIn {
            from {
              opacity: 0;
              transform: scale(0.95);
            }
            to {
              opacity: 1;
              transform: scale(1);
            }
          }
          @keyframes spin {
            from {
              transform: rotate(0deg);
            }
            to {
              transform: rotate(360deg);
            }
          }
        `}</style>

        {/* Select Products Step */}
        {step === 'select' && (
          <ProductSelector
            onProductsSelected={handleProductsSelected}
            onBack={onClose}
          />
        )}

        {/* Loading Step */}
        {step === 'loading' && (
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            height: '100%',
            padding: '60px 40px',
            gap: 24,
          }}>
            <div style={{
              fontSize: 48,
              animation: 'fadeInOut 2s ease-in-out infinite',
            }}>
              🔄
            </div>
            <Loader
              size={48}
              color="#667eea"
              style={{ animation: 'spin 2s linear infinite' }}
            />
            <div style={{
              fontSize: 18,
              fontWeight: 600,
              color: '#1f2937',
              textAlign: 'center',
            }}>
              Analyzing Products...
            </div>
            <div style={{
              fontSize: 14,
              color: '#6b7280',
              textAlign: 'center',
              maxWidth: 300,
            }}>
              Our AI is comparing specifications, prices, and features to give you the best recommendations.
            </div>

            {/* Progress dots */}
            <div style={{
              display: 'flex',
              gap: 8,
              marginTop: 20,
            }}>
              {[0, 1, 2].map((i) => (
                <div
                  key={i}
                  style={{
                    width: 8,
                    height: 8,
                    borderRadius: '50%',
                    background: '#e5e7eb',
                    animation: `pulse ${0.6}s ease-in-out ${i * 0.2}s infinite`,
                  }}
                />
              ))}
            </div>

            <style>{`
              @keyframes fadeInOut {
                0%, 100% {
                  opacity: 1;
                }
                50% {
                  opacity: 0.5;
                }
              }
              @keyframes pulse {
                0%, 100% {
                  background: #e5e7eb;
                  transform: scale(1);
                }
                50% {
                  background: #667eea;
                  transform: scale(1.2);
                }
              }
            `}</style>
          </div>
        )}

        {/* Result Step */}
        {step === 'result' && comparisonData && (
          <ComparisonResult
            data={comparisonData}
            onBack={handleBack}
          />
        )}

        {/* Error State */}
        {error && (
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            height: '100%',
            padding: '40px',
            gap: 20,
          }}>
            <div style={{
              fontSize: 32,
            }}>
              ⚠️
            </div>
            <div style={{
              fontSize: 16,
              fontWeight: 600,
              color: '#dc2626',
              textAlign: 'center',
            }}>
              Something went wrong
            </div>
            <div style={{
              fontSize: 14,
              color: '#6b7280',
              textAlign: 'center',
              maxWidth: 400,
            }}>
              {error}
            </div>
            <button
              onClick={handleBack}
              style={{
                marginTop: 20,
                padding: '12px 24px',
                background: '#667eea',
                color: '#fff',
                border: 'none',
                borderRadius: 8,
                fontWeight: 600,
                cursor: 'pointer',
                fontFamily: 'inherit',
                transition: 'all 0.2s',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = '#5568d3';
                e.currentTarget.style.transform = 'translateY(-2px)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = '#667eea';
                e.currentTarget.style.transform = 'translateY(0)';
              }}
            >
              Go Back
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
