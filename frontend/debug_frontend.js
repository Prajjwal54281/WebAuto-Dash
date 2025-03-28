#!/usr/bin/env node

/**
 * Frontend Debug Script
 * Tests if WebAutoDash frontend and backend are working properly
 */

const http = require('http');

function makeRequest(url) {
    return new Promise((resolve, reject) => {
        const urlObj = new URL(url);
        const options = {
            hostname: urlObj.hostname,
            port: urlObj.port,
            path: urlObj.pathname + urlObj.search,
            method: 'GET',
            headers: {
                'User-Agent': 'WebAutoDash-Debug/1.0',
                'Accept': 'application/json,text/html',
                'Origin': 'http://localhost:3009'
            }
        };

        const req = http.request(options, (res) => {
            let data = '';
            res.on('data', (chunk) => data += chunk);
            res.on('end', () => {
                resolve({
                    status: res.statusCode,
                    headers: res.headers,
                    data: data.substring(0, 500) // First 500 chars
                });
            });
        });

        req.on('error', reject);
        req.setTimeout(5000, () => {
            req.destroy();
            reject(new Error('Request timeout'));
        });
        req.end();
    });
}

async function testEndpoint(name, url) {
    try {
        console.log(`🔍 Testing ${name}...`);
        const result = await makeRequest(url);
        console.log(`✅ ${name}: HTTP ${result.status}`);

        if (result.status === 200) {
            // Check if it's JSON
            try {
                const json = JSON.parse(result.data);
                console.log(`   📋 Response: ${JSON.stringify(json).substring(0, 100)}...`);
            } catch (e) {
                // HTML response
                if (result.data.includes('<title>')) {
                    const title = result.data.match(/<title>(.*?)<\/title>/);
                    console.log(`   📄 HTML Page: ${title ? title[1] : 'Unknown'}`);
                } else {
                    console.log(`   📄 Response: ${result.data.substring(0, 100)}...`);
                }
            }
        } else {
            console.log(`   ❌ Error: HTTP ${result.status}`);
        }
    } catch (error) {
        console.log(`❌ ${name}: ${error.message}`);
    }
    console.log('');
}

async function runDiagnostics() {
    console.log('🚀 WebAutoDash Frontend Diagnostics\n');

    // Test frontend
    await testEndpoint('Frontend (React App)', 'http://localhost:3009');

    // Test backend health
    await testEndpoint('Backend Health', 'http://localhost:5005/api/health');

    // Test backend jobs API
    await testEndpoint('Backend Jobs API', 'http://localhost:5005/api/jobs');

    // Test new patient data API
    await testEndpoint('Patient Data API', 'http://localhost:5005/api/patient-data/health');

    console.log('✅ Diagnostics complete!');
    console.log('\n💡 If frontend shows "Loading..." or blank page:');
    console.log('   1. Open browser dev tools (F12)');
    console.log('   2. Check Console tab for JavaScript errors');
    console.log('   3. Check Network tab for failed API calls');
    console.log('   4. Try visiting: http://localhost:3009');
}

runDiagnostics().catch(console.error); 