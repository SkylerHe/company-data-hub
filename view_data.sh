#!/bin/bash
# Interactive data viewer - browse collected news and filings

cd "$(dirname "$0")"
source venv/bin/activate

show_menu() {
    echo ""
    echo "=================================================="
    echo "  COMPANY DATA VIEWER"
    echo "=================================================="
    echo ""
    echo "1) View latest news articles"
    echo "2) View latest SEC filings"
    echo "3) View data for a specific company"
    echo "4) Search news by keyword"
    echo "5) Show database statistics"
    echo "6) Exit"
    echo ""
    read -p "Choose option (1-6): " choice
    echo ""
}

view_latest_news() {
    echo "📰 LATEST 10 NEWS ARTICLES:"
    echo "=================================================="
    sqlite3 finance.db "
    SELECT
        substr(c.name, 1, 20) as company,
        substr(n.title, 1, 60) as title,
        date(n.published_at) as date,
        n.source
    FROM news n
    JOIN companies c ON n.company_id = c.id
    ORDER BY n.fetched_at DESC
    LIMIT 10
    " -header -column
}

view_latest_filings() {
    echo "📄 LATEST 10 SEC FILINGS:"
    echo "=================================================="
    sqlite3 finance.db "
    SELECT
        substr(c.name, 1, 20) as company,
        f.type,
        date(f.date) as filing_date,
        substr(f.title, 1, 40) as title
    FROM filings f
    JOIN companies c ON f.company_id = c.id
    ORDER BY f.fetched_at DESC
    LIMIT 10
    " -header -column
}

view_company_data() {
    echo "Available companies:"
    sqlite3 finance.db "
    SELECT name FROM companies
    WHERE id IN (SELECT DISTINCT company_id FROM news)
       OR id IN (SELECT DISTINCT company_id FROM filings)
    ORDER BY name
    LIMIT 20
    "
    echo ""
    read -p "Enter company name (exact match): " company_name
    echo ""

    echo "📊 DATA FOR: $company_name"
    echo "=================================================="

    # News count
    news_count=$(sqlite3 finance.db "
    SELECT COUNT(*) FROM news
    WHERE company_id = (SELECT id FROM companies WHERE name = '$company_name')
    ")
    echo "News articles: $news_count"

    # Filing count
    filing_count=$(sqlite3 finance.db "
    SELECT COUNT(*) FROM filings
    WHERE company_id = (SELECT id FROM companies WHERE name = '$company_name')
    ")
    echo "SEC filings: $filing_count"
    echo ""

    if [ "$news_count" -gt 0 ]; then
        echo "Recent news:"
        sqlite3 finance.db "
        SELECT
            date(published_at) as date,
            substr(title, 1, 70) as title
        FROM news
        WHERE company_id = (SELECT id FROM companies WHERE name = '$company_name')
        ORDER BY published_at DESC
        LIMIT 5
        " -column
        echo ""
    fi

    if [ "$filing_count" -gt 0 ]; then
        echo "Recent filings:"
        sqlite3 finance.db "
        SELECT
            type,
            date(date) as filing_date,
            substr(title, 1, 50) as title
        FROM filings
        WHERE company_id = (SELECT id FROM companies WHERE name = '$company_name')
        ORDER BY date DESC
        LIMIT 5
        " -column
    fi
}

search_news() {
    read -p "Enter search keyword: " keyword
    echo ""
    echo "🔍 NEWS MATCHING '$keyword':"
    echo "=================================================="
    sqlite3 finance.db "
    SELECT
        substr(c.name, 1, 15) as company,
        date(n.published_at) as date,
        substr(n.title, 1, 60) as title
    FROM news n
    JOIN companies c ON n.company_id = c.id
    WHERE n.title LIKE '%$keyword%' OR n.content LIKE '%$keyword%'
    ORDER BY n.published_at DESC
    LIMIT 20
    " -header -column
}

show_stats() {
    python store.py --stats
}

# Main loop
while true; do
    show_menu

    case $choice in
        1)
            view_latest_news
            ;;
        2)
            view_latest_filings
            ;;
        3)
            view_company_data
            ;;
        4)
            search_news
            ;;
        5)
            show_stats
            ;;
        6)
            echo "Goodbye!"
            exit 0
            ;;
        *)
            echo "Invalid option. Please choose 1-6."
            ;;
    esac

    echo ""
    read -p "Press Enter to continue..."
done
