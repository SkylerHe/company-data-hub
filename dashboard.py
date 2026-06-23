#!/usr/bin/env python3
"""
Simple web dashboard to view collected company data.
Run with: python dashboard.py
Then open: http://localhost:8000
"""

import sqlite3
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
import json

DB_PATH = "finance.db"


def get_db():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    return db


class DashboardHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Suppress default logging
        pass

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == '/':
            self.serve_html()
        elif parsed.path == '/api/stats':
            self.serve_stats()
        elif parsed.path == '/api/industries':
            self.serve_industries()
        elif parsed.path == '/api/companies':
            self.serve_companies(parsed.query)
        elif parsed.path == '/api/news':
            self.serve_news(parsed.query)
        elif parsed.path == '/api/filings':
            self.serve_filings(parsed.query)
        elif parsed.path == '/api/timeline':
            self.serve_timeline()
        else:
            self.send_error(404)

    def serve_html(self):
        html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Company Data Hub - Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #f5f5f7;
            color: #1d1d1f;
            padding: 20px;
        }
        .header {
            background: white;
            padding: 30px;
            border-radius: 12px;
            margin-bottom: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }
        h1 { font-size: 32px; font-weight: 600; margin-bottom: 10px; }
        .subtitle { color: #6e6e73; font-size: 16px; }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }
        .stat-card {
            background: white;
            padding: 24px;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }
        .stat-number {
            font-size: 36px;
            font-weight: 600;
            color: #0071e3;
            margin-bottom: 8px;
        }
        .stat-label {
            font-size: 14px;
            color: #6e6e73;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .content-grid {
            display: grid;
            grid-template-columns: 300px 1fr;
            gap: 20px;
        }

        .sidebar {
            background: white;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            max-height: calc(100vh - 300px);
            overflow-y: auto;
        }
        .sidebar h2 {
            font-size: 18px;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 1px solid #e5e5e7;
        }

        .industry-item {
            padding: 12px;
            margin-bottom: 8px;
            background: #f5f5f7;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.2s;
        }
        .industry-item:hover {
            background: #e8e8ed;
            transform: translateX(4px);
        }
        .industry-item.active {
            background: #0071e3;
            color: white;
        }
        .industry-name {
            font-weight: 500;
            font-size: 14px;
            margin-bottom: 4px;
        }
        .industry-count {
            font-size: 12px;
            opacity: 0.7;
        }

        .main-content {
            background: white;
            padding: 30px;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            max-height: calc(100vh - 300px);
            overflow-y: auto;
        }
        .main-content h2 {
            font-size: 24px;
            margin-bottom: 20px;
        }

        .company-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }
        .company-card {
            padding: 16px;
            background: #f5f5f7;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.2s;
        }
        .company-card:hover {
            background: #e8e8ed;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }
        .company-name {
            font-weight: 600;
            margin-bottom: 8px;
        }
        .company-stats {
            font-size: 12px;
            color: #6e6e73;
        }

        .timeline {
            margin-top: 30px;
        }
        .timeline-item {
            padding: 16px;
            margin-bottom: 12px;
            background: #f5f5f7;
            border-radius: 8px;
            border-left: 4px solid #0071e3;
        }
        .timeline-date {
            font-size: 12px;
            color: #6e6e73;
            margin-bottom: 4px;
        }
        .timeline-title {
            font-weight: 500;
            margin-bottom: 4px;
        }
        .timeline-source {
            font-size: 12px;
            color: #6e6e73;
        }
        .filing-badge {
            display: inline-block;
            padding: 4px 8px;
            background: #0071e3;
            color: white;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
            margin-right: 8px;
        }

        .tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            border-bottom: 1px solid #e5e5e7;
            padding-bottom: 10px;
        }
        .tab {
            padding: 8px 16px;
            background: none;
            border: none;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            color: #6e6e73;
            border-radius: 6px;
            transition: all 0.2s;
        }
        .tab:hover {
            background: #f5f5f7;
        }
        .tab.active {
            background: #0071e3;
            color: white;
        }

        .loading {
            text-align: center;
            padding: 40px;
            color: #6e6e73;
        }

        @media (max-width: 768px) {
            .content-grid {
                grid-template-columns: 1fr;
            }
            .company-grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 Company Data Hub</h1>
        <div class="subtitle">Real-time equity research data collection system</div>
    </div>

    <div class="stats-grid" id="stats">
        <div class="loading">Loading statistics...</div>
    </div>

    <div class="content-grid">
        <div class="sidebar">
            <h2>Industries</h2>
            <div id="industries">
                <div class="loading">Loading...</div>
            </div>
        </div>

        <div class="main-content">
            <div class="tabs">
                <button class="tab active" onclick="showTab('companies')">Companies</button>
                <button class="tab" onclick="showTab('news')">Latest News</button>
                <button class="tab" onclick="showTab('filings')">Latest Filings</button>
            </div>

            <div id="tab-content">
                <div class="loading">Select an industry to view companies</div>
            </div>
        </div>
    </div>

    <script>
        let selectedIndustry = null;
        let currentTab = 'companies';

        async function loadStats() {
            const res = await fetch('/api/stats');
            const stats = await res.json();

            document.getElementById('stats').innerHTML = `
                <div class="stat-card">
                    <div class="stat-number">${stats.companies}</div>
                    <div class="stat-label">Companies</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">${stats.industries}</div>
                    <div class="stat-label">Industries</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">${stats.news}</div>
                    <div class="stat-label">News Articles</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">${stats.filings}</div>
                    <div class="stat-label">SEC Filings</div>
                </div>
            `;
        }

        async function loadIndustries() {
            const res = await fetch('/api/industries');
            const industries = await res.json();

            document.getElementById('industries').innerHTML = industries.map(ind => `
                <div class="industry-item" onclick="selectIndustry('${ind.name}')">
                    <div class="industry-name">${ind.name}</div>
                    <div class="industry-count">${ind.company_count} companies • ${ind.total_items} items</div>
                </div>
            `).join('');
        }

        function selectIndustry(industry) {
            selectedIndustry = industry;

            // Update active state
            document.querySelectorAll('.industry-item').forEach(el => {
                el.classList.remove('active');
            });
            event.target.closest('.industry-item').classList.add('active');

            // Load content based on current tab
            if (currentTab === 'companies') {
                loadCompanies(industry);
            } else if (currentTab === 'news') {
                loadNews(industry);
            } else if (currentTab === 'filings') {
                loadFilings(industry);
            }
        }

        async function loadCompanies(industry) {
            document.getElementById('tab-content').innerHTML = '<div class="loading">Loading companies...</div>';

            const res = await fetch(`/api/companies?industry=${encodeURIComponent(industry)}`);
            const companies = await res.json();

            document.getElementById('tab-content').innerHTML = `
                <h2>${industry}</h2>
                <div class="company-grid">
                    ${companies.map(c => `
                        <div class="company-card">
                            <div class="company-name">${c.name}</div>
                            <div class="company-stats">
                                ${c.ticker ? `<span>${c.ticker}</span> • ` : ''}
                                ${c.news_count} news • ${c.filing_count} filings
                            </div>
                        </div>
                    `).join('')}
                </div>
            `;
        }

        async function loadNews(industry) {
            document.getElementById('tab-content').innerHTML = '<div class="loading">Loading news...</div>';

            const res = await fetch(`/api/news?industry=${encodeURIComponent(industry)}`);
            const news = await res.json();

            document.getElementById('tab-content').innerHTML = `
                <h2>Latest News - ${industry}</h2>
                <div class="timeline">
                    ${news.map(item => `
                        <div class="timeline-item">
                            <div class="timeline-date">${item.published_at} • ${item.company}</div>
                            <div class="timeline-title">${item.title}</div>
                            <div class="timeline-source">${item.source || 'Unknown source'}</div>
                        </div>
                    `).join('')}
                </div>
            `;
        }

        async function loadFilings(industry) {
            document.getElementById('tab-content').innerHTML = '<div class="loading">Loading filings...</div>';

            const res = await fetch(`/api/filings?industry=${encodeURIComponent(industry)}`);
            const filings = await res.json();

            document.getElementById('tab-content').innerHTML = `
                <h2>Latest SEC Filings - ${industry}</h2>
                <div class="timeline">
                    ${filings.map(item => `
                        <div class="timeline-item">
                            <div class="timeline-date">${item.date} • ${item.company}</div>
                            <div class="timeline-title">
                                <span class="filing-badge">${item.type}</span>
                                ${item.title}
                            </div>
                        </div>
                    `).join('')}
                </div>
            `;
        }

        function showTab(tab) {
            currentTab = tab;

            // Update active tab
            document.querySelectorAll('.tab').forEach(el => {
                el.classList.remove('active');
            });
            event.target.classList.add('active');

            // Load content
            if (!selectedIndustry) {
                document.getElementById('tab-content').innerHTML = '<div class="loading">Select an industry first</div>';
                return;
            }

            if (tab === 'companies') {
                loadCompanies(selectedIndustry);
            } else if (tab === 'news') {
                loadNews(selectedIndustry);
            } else if (tab === 'filings') {
                loadFilings(selectedIndustry);
            }
        }

        // Load initial data
        loadStats();
        loadIndustries();
    </script>
</body>
</html>"""

        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(html.encode())

    def serve_stats(self):
        db = get_db()
        stats = {
            'companies': db.execute('SELECT COUNT(*) FROM companies').fetchone()[0],
            'industries': db.execute('SELECT COUNT(*) FROM industries').fetchone()[0],
            'news': db.execute('SELECT COUNT(*) FROM news').fetchone()[0],
            'filings': db.execute('SELECT COUNT(*) FROM filings').fetchone()[0],
        }
        self.send_json(stats)

    def serve_industries(self):
        db = get_db()
        rows = db.execute("""
            SELECT
                i.name,
                COUNT(DISTINCT ci.company_id) as company_count,
                (SELECT COUNT(*) FROM news n
                 JOIN company_industries ci2 ON n.company_id = ci2.company_id
                 WHERE ci2.industry_id = i.id) +
                (SELECT COUNT(*) FROM filings f
                 JOIN company_industries ci3 ON f.company_id = ci3.company_id
                 WHERE ci3.industry_id = i.id) as total_items
            FROM industries i
            LEFT JOIN company_industries ci ON i.id = ci.industry_id
            GROUP BY i.id
            ORDER BY i.name
        """).fetchall()

        industries = [dict(row) for row in rows]
        self.send_json(industries)

    def serve_companies(self, query):
        params = parse_qs(query)
        industry = params.get('industry', [''])[0]

        db = get_db()
        rows = db.execute("""
            SELECT
                c.name,
                c.ticker,
                COUNT(DISTINCT n.id) as news_count,
                COUNT(DISTINCT f.id) as filing_count
            FROM companies c
            JOIN company_industries ci ON c.id = ci.company_id
            JOIN industries i ON ci.industry_id = i.id
            LEFT JOIN news n ON c.id = n.company_id
            LEFT JOIN filings f ON c.id = f.company_id
            WHERE i.name = ?
            GROUP BY c.id
            ORDER BY c.name
        """, (industry,)).fetchall()

        companies = [dict(row) for row in rows]
        self.send_json(companies)

    def serve_news(self, query):
        params = parse_qs(query)
        industry = params.get('industry', [''])[0]

        db = get_db()
        rows = db.execute("""
            SELECT
                c.name as company,
                n.title,
                n.source,
                n.published_at,
                n.url
            FROM news n
            JOIN companies c ON n.company_id = c.id
            JOIN company_industries ci ON c.id = ci.company_id
            JOIN industries i ON ci.industry_id = i.id
            WHERE i.name = ?
            ORDER BY n.published_at DESC
            LIMIT 50
        """, (industry,)).fetchall()

        news = [dict(row) for row in rows]
        self.send_json(news)

    def serve_filings(self, query):
        params = parse_qs(query)
        industry = params.get('industry', [''])[0]

        db = get_db()
        rows = db.execute("""
            SELECT
                c.name as company,
                f.type,
                f.title,
                f.date,
                f.url
            FROM filings f
            JOIN companies c ON f.company_id = c.id
            JOIN company_industries ci ON c.id = ci.company_id
            JOIN industries i ON ci.industry_id = i.id
            WHERE i.name = ?
            ORDER BY f.date DESC
            LIMIT 50
        """, (industry,)).fetchall()

        filings = [dict(row) for row in rows]
        self.send_json(filings)

    def serve_timeline(self):
        db = get_db()
        rows = db.execute("""
            SELECT date(fetched_at) as date, COUNT(*) as count
            FROM news
            GROUP BY date
            ORDER BY date DESC
            LIMIT 30
        """).fetchall()

        timeline = [dict(row) for row in rows]
        self.send_json(timeline)

    def send_json(self, data):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())


def main():
    PORT = 8000
    server = HTTPServer(('localhost', PORT), DashboardHandler)
    print(f"""
╔════════════════════════════════════════════════════════════╗
║                                                            ║
║   📊  COMPANY DATA HUB DASHBOARD                          ║
║                                                            ║
║   Dashboard is running at:                                ║
║   👉  http://localhost:{PORT}                                ║
║                                                            ║
║   Press Ctrl+C to stop the server                         ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
    """)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\n✓ Dashboard stopped")
        server.shutdown()


if __name__ == '__main__':
    main()
