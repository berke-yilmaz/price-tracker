// utils/networkDiagnostics.js - Network debugging helper
import config from '../config';

export const NetworkDiagnostics = {
  
  // Test basic connectivity
  async testConnection() {
    const results = {
      timestamp: new Date().toISOString(),
      config: {
        API_URL: config.API_URL,
        BASE_URL: config.BASE_URL,
        timeout: config.TIMEOUT
      },
      tests: {}
    };

    console.log('🔍 Starting network diagnostics...');
    console.log('📡 Testing:', config.API_URL);

    // Test 1: Basic connectivity
    try {
      const response = await fetch(config.BASE_URL, {
        method: 'GET',
        timeout: 5000
      });
      
      results.tests.baseConnection = {
        success: true,
        status: response.status,
        statusText: response.statusText,
        url: config.BASE_URL
      };
      
      console.log('✅ Base connection test passed:', response.status);
    } catch (error) {
      results.tests.baseConnection = {
        success: false,
        error: error.message,
        url: config.BASE_URL
      };
      
      console.error('❌ Base connection test failed:', error.message);
    }

    // Test 2: API endpoint
    try {
      const response = await fetch(`${config.API_URL}/`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        timeout: 5000
      });
      
      results.tests.apiConnection = {
        success: response.ok,
        status: response.status,
        statusText: response.statusText,
        url: `${config.API_URL}/`
      };
      
      console.log('✅ API connection test:', response.status);
    } catch (error) {
      results.tests.apiConnection = {
        success: false,
        error: error.message,
        url: `${config.API_URL}/`
      };
      
      console.error('❌ API connection test failed:', error.message);
    }

    // Test 3: Products endpoint
    try {
      const response = await fetch(`${config.API_URL}/products/`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        timeout: 5000
      });
      
      results.tests.productsEndpoint = {
        success: response.ok,
        status: response.status,
        statusText: response.statusText,
        url: `${config.API_URL}/products/`
      };
      
      if (response.ok) {
        const data = await response.json();
        results.tests.productsEndpoint.dataReceived = true;
        results.tests.productsEndpoint.productCount = data.results?.length || data.length || 0;
      }
      
      console.log('✅ Products endpoint test:', response.status);
    } catch (error) {
      results.tests.productsEndpoint = {
        success: false,
        error: error.message,
        url: `${config.API_URL}/products/`
      };
      
      console.error('❌ Products endpoint test failed:', error.message);
    }

    // Test 4: Stores endpoint
    try {
      const response = await fetch(`${config.API_URL}/stores/`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        timeout: 5000
      });
      
      results.tests.storesEndpoint = {
        success: response.ok,
        status: response.status,
        statusText: response.statusText,
        url: `${config.API_URL}/stores/`
      };
      
      console.log('📊 Stores endpoint test:', response.status);
    } catch (error) {
      results.tests.storesEndpoint = {
        success: false,
        error: error.message,
        url: `${config.API_URL}/stores/`
      };
      
      console.error('❌ Stores endpoint test failed:', error.message);
    }

    return results;
  },

  // Get diagnostic summary
  getSummary(results) {
    const totalTests = Object.keys(results.tests).length;
    const passedTests = Object.values(results.tests).filter(test => test.success).length;
    
    return {
      overall: passedTests === totalTests ? 'PASS' : 'FAIL',
      score: `${passedTests}/${totalTests}`,
      percentage: Math.round((passedTests / totalTests) * 100),
      recommendations: this.getRecommendations(results)
    };
  },

  // Get troubleshooting recommendations
  getRecommendations(results) {
    const recommendations = [];

    if (!results.tests.baseConnection?.success) {
      recommendations.push('❌ Cannot reach backend server - check if Django is running');
      recommendations.push('💡 Run: python manage.py runserver 0.0.0.0:8000');
      
      if (config.API_URL.includes('ngrok')) {
        recommendations.push('🔧 Update ngrok URL in config/index.js');
        recommendations.push('💡 Get new URL from: ngrok http 8000');
      }
    }

    if (!results.tests.apiConnection?.success) {
      recommendations.push('❌ API endpoint not found - check URL configuration');
      recommendations.push('💡 Verify API_URL in config/index.js matches Django URL patterns');
    }

    if (!results.tests.productsEndpoint?.success) {
      recommendations.push('❌ Products API not working - check Django API setup');
      recommendations.push('💡 Verify api/urls.py and api/views.py are configured correctly');
    }

    if (!results.tests.storesEndpoint?.success) {
      recommendations.push('❌ Stores API causing "Mağaza alım hatası" error');
      recommendations.push('💡 This is likely the source of your StoreSelector error');
    }

    if (recommendations.length === 0) {
      recommendations.push('✅ All network tests passed!');
      recommendations.push('🔍 Image loading issues may be due to:');
      recommendations.push('   • Image URLs are malformed');
      recommendations.push('   • CORS settings for media files');
      recommendations.push('   • Django MEDIA_URL configuration');
    }

    return recommendations;
  },

  // Print detailed report
  printReport(results) {
    console.log('\n🔍 NETWORK DIAGNOSTICS REPORT');
    console.log('==============================');
    console.log('Timestamp:', results.timestamp);
    console.log('API URL:', results.config.API_URL);
    console.log('');

    Object.entries(results.tests).forEach(([testName, result]) => {
      const status = result.success ? '✅ PASS' : '❌ FAIL';
      console.log(`${status} ${testName}`);
      console.log(`   URL: ${result.url}`);
      
      if (result.success) {
        console.log(`   Status: ${result.status} ${result.statusText}`);
        if (result.productCount !== undefined) {
          console.log(`   Products found: ${result.productCount}`);
        }
      } else {
        console.log(`   Error: ${result.error}`);
      }
      console.log('');
    });

    const summary = this.getSummary(results);
    console.log('SUMMARY:', summary.overall, `(${summary.score})`);
    console.log('');
    console.log('RECOMMENDATIONS:');
    summary.recommendations.forEach(rec => console.log(rec));
    console.log('');
  }
};

// Usage example for debugging:
/*
import { NetworkDiagnostics } from '../utils/networkDiagnostics';

// In your component or debugging session:
const runDiagnostics = async () => {
  const results = await NetworkDiagnostics.testConnection();
  NetworkDiagnostics.printReport(results);
  return results;
};
*/

export default NetworkDiagnostics;