/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  transpilePackages: ['@deck.gl/layers', '@deck.gl/react', '@deck.gl/core'],
  webpack: (config) => {
    config.resolve.alias = {
      ...config.resolve.alias,
      'mapbox-gl': 'mapbox-gl'
    };
    return config;
  }
};

module.exports = nextConfig;
