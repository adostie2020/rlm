/** @type {import('next').NextConfig} */
const nextConfig = {
  rewrites: async () => {
    return {
      fallback: [
        {
          source: '/api/:path((?!auth).*)',
          destination:
            process.env.NODE_ENV === 'development'
              ? 'http://127.0.0.1:8000/api/:path'
              : `${process.env.RLM_BACKEND_URL || 'https://your-render-backend-url.onrender.com'}/api/:path`,
        },
        {
          source: '/docs',
          destination:
            process.env.NODE_ENV === 'development'
              ? 'http://127.0.0.1:8000/docs'
              : `${process.env.RLM_BACKEND_URL || 'https://your-render-backend-url.onrender.com'}/docs`,
        },
        {
          source: '/openapi.json',
          destination:
            process.env.NODE_ENV === 'development'
              ? 'http://127.0.0.1:8000/openapi.json'
              : `${process.env.RLM_BACKEND_URL || 'https://your-render-backend-url.onrender.com'}/openapi.json`,
        },
      ],
    };
  },
};

module.exports = nextConfig;
