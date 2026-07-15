#!/usr/bin/env python3
"""
Redesigned dashboard focused on insights and readability.
Run with: python dashboard_v2.py
Then open: http://localhost:8000
"""

import sqlite3
import json
import re
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

DB_PATH = "finance.db"


def get_db():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    return db


def summarize_text(text, max_paragraphs=2):
    """Extract first 1-2 paragraphs as insightful summary (where, why, how, who, what)."""
    if not text:
        return "No content available"

    # Clean up text
    text = text.strip()

    # Try to split by paragraphs first
    paragraphs = re.split(r'\n\s*\n', text)

    # If no clear paragraphs, fall back to sentences
    if len(paragraphs) == 1:
        sentences = re.split(r'[.!?]+\s+', text)
        # Take 5-8 sentences for a meaningful summary
        summary_sentences = sentences[:8]
        summary = '. '.join(s for s in summary_sentences if s.strip())
        if summary and not summary.endswith('.'):
            summary += '.'
    else:
        # Take first 1-2 paragraphs
        summary = '\n\n'.join(paragraphs[:max_paragraphs])

    # Limit to reasonable length (1500 chars for 1-2 paragraphs)
    if len(summary) > 1500:
        summary = summary[:1500] + "..."

    return summary


class DashboardHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == '/':
            self.serve_html()
        elif parsed.path == '/api/industries':
            self.serve_industries()
        elif parsed.path == '/api/content':
            self.serve_content(parsed.query)
        else:
            self.send_error(404)

    def serve_html(self):
        html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Research</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #fafafa;
            color: #1a1a1a;
            line-height: 1.6;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }

        /* Sidebar */
        .sidebar {
            position: fixed;
            left: 0;
            top: 0;
            width: 240px;
            height: 100vh;
            background: white;
            border-right: 1px solid #e0e0e0;
            overflow-y: auto;
            padding: 20px;
        }

        .sidebar h3 {
            font-size: 13px;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 15px;
            font-weight: 600;
        }

        .industry-list {
            list-style: none;
        }

        .industry-item {
            padding: 10px 12px;
            margin-bottom: 4px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.2s;
            color: #333;
        }

        .industry-item:hover {
            background: #f5f5f5;
        }

        .industry-item.active {
            background: #0066cc;
            color: white;
        }

        .industry-count {
            font-size: 12px;
            opacity: 0.6;
            margin-left: 4px;
        }

        /* Main content */
        .main {
            margin-left: 260px;
            padding: 20px;
        }

        .breadcrumb {
            font-size: 13px;
            color: #666;
            margin-bottom: 20px;
        }

        .breadcrumb span {
            color: #333;
            font-weight: 500;
        }

        /* Content cards */
        .content-list {
            display: grid;
            gap: 20px;
        }

        .content-card {
            background: white;
            border-radius: 8px;
            padding: 24px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            border-left: 3px solid #0066cc;
            margin-bottom: 20px;
        }

        .content-meta {
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 12px;
            font-size: 13px;
            color: #666;
        }

        .badge {
            background: #0066cc;
            color: white;
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
        }

        .badge.news { background: #0066cc; }
        .badge.filing-10k { background: #d14343; }
        .badge.filing-10q { background: #f59e0b; }
        .badge.filing-8k { background: #10b981; }

        .company-tag {
            background: #f0f0f0;
            color: #555;
            padding: 3px 10px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 500;
        }

        .content-title {
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 12px;
            line-height: 1.4;
        }

        .content-title a {
            color: #0066cc;
            text-decoration: none;
            transition: color 0.2s;
        }

        .content-title a:hover {
            color: #0052a3;
            text-decoration: underline;
        }

        .content-summary {
            color: #333;
            font-size: 15px;
            line-height: 1.7;
            margin-bottom: 0;
            white-space: pre-wrap;
        }

        .loading {
            text-align: center;
            padding: 60px 20px;
            color: #999;
        }

        .empty-state {
            text-align: center;
            padding: 60px 20px;
            color: #999;
        }

        .empty-state-icon {
            font-size: 48px;
            margin-bottom: 16px;
        }

        @media (max-width: 768px) {
            .sidebar {
                position: static;
                width: 100%;
                height: auto;
                border-right: none;
                border-bottom: 1px solid #e0e0e0;
            }
            .main {
                margin-left: 0;
            }
        }
    </style>
</head>
<body>
    <div class="sidebar">
        <h3>Industries</h3>
        <ul class="industry-list" id="industries">
            <li class="loading">Loading...</li>
        </ul>
    </div>

    <div class="main">
        <div class="breadcrumb">
            <span id="current-industry">Select an industry</span>
        </div>

        <div class="content-list" id="content">
            <div class="empty-state">
                <div class="empty-state-icon">📊</div>
                <div>Select an industry to view research content</div>
            </div>
        </div>
    </div>

    <script>
        let currentData = [];

        async function loadIndustries() {
            const res = await fetch('/api/industries');
            const industries = await res.json();

            document.getElementById('industries').innerHTML = industries.map(ind => `
                <li class="industry-item" onclick="selectIndustry('${ind.name}', event)">
                    ${ind.name}
                    <span class="industry-count">(${ind.total_items})</span>
                </li>
            `).join('');
        }

        async function selectIndustry(industry, event) {
            // Update active state
            document.querySelectorAll('.industry-item').forEach(el => el.classList.remove('active'));
            event.target.classList.add('active');

            // Update breadcrumb
            document.getElementById('current-industry').textContent = industry;

            // Load content
            document.getElementById('content').innerHTML = '<div class="loading">Loading content...</div>';

            const res = await fetch(`/api/content?industry=${encodeURIComponent(industry)}`);
            const data = await res.json();
            currentData = data;

            if (data.length === 0) {
                document.getElementById('content').innerHTML = `
                    <div class="empty-state">
                        <div class="empty-state-icon">📭</div>
                        <div>No content available for this industry yet</div>
                    </div>
                `;
                return;
            }

            document.getElementById('content').innerHTML = data.map((item, idx) => {
                const badgeClass = item.type === 'news' ? 'news' :
                                  item.filing_type === '10-K' ? 'filing-10k' :
                                  item.filing_type === '10-Q' ? 'filing-10q' : 'filing-8k';

                const badgeText = item.type === 'news' ? 'News' : item.filing_type;

                return `
                    <div class="content-card">
                        <div class="content-meta">
                            <span class="badge ${badgeClass}">${badgeText}</span>
                            <span class="company-tag">${item.company}</span>
                            <span>${item.date}</span>
                            ${item.source ? `<span>•</span><span>${item.source}</span>` : ''}
                        </div>
                        <div class="content-title">
                            <a href="${item.url}" target="_blank">${item.title}</a>
                        </div>
                        <div class="content-summary">${item.summary}</div>
                    </div>
                `;
            }).join('');
        }

        loadIndustries();
    </script>
</body>
</html>"""

        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(html.encode())

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

    def serve_content(self, query):
        params = parse_qs(query)
        industry = params.get('industry', [''])[0]

        db = get_db()

        # Get news
        news = db.execute("""
            SELECT
                'news' as type,
                c.name as company,
                n.title,
                n.source,
                n.published_at as date,
                n.url,
                n.content,
                NULL as filing_type
            FROM news n
            JOIN companies c ON n.company_id = c.id
            JOIN company_industries ci ON c.id = ci.company_id
            JOIN industries i ON ci.industry_id = i.id
            WHERE i.name = ?
            ORDER BY n.published_at DESC
            LIMIT 30
        """, (industry,)).fetchall()

        # Get filings
        filings = db.execute("""
            SELECT
                'filing' as type,
                c.name as company,
                f.title,
                NULL as source,
                f.date,
                f.url,
                f.content,
                f.type as filing_type
            FROM filings f
            JOIN companies c ON f.company_id = c.id
            JOIN company_industries ci ON c.id = ci.company_id
            JOIN industries i ON ci.industry_id = i.id
            WHERE i.name = ?
            ORDER BY f.date DESC
            LIMIT 30
        """, (industry,)).fetchall()

        # Combine and sort
        all_content = []

        for row in news:
            item = dict(row)
            item['summary'] = summarize_text(item.get('content', ''))
            all_content.append(item)

        for row in filings:
            item = dict(row)
            item['summary'] = summarize_text(item.get('content', ''))
            all_content.append(item)

        # Sort by date
        all_content.sort(key=lambda x: x['date'] or '', reverse=True)

        self.send_json(all_content)

    def send_json(self, data):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())


def main():
    PORT = 8000
    server = HTTPServer(('localhost', PORT), DashboardHandler)
    print(f"""
╔═══════════════════════════════════════════╗
║  Research Dashboard                       ║
║  http://localhost:{PORT}                     ║
║  Press Ctrl+C to stop                     ║
╚═══════════════════════════════════════════╝
    """)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n✓ Stopped")
        server.shutdown()


if __name__ == '__main__':
    main()
