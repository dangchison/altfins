# -*- coding: utf-8 -*-
"""
scraper/patterns_extractor.py

Handles extraction of data from 'altfins-trading-pattern-component' cards,
which are used in both 'Chart Patterns' and 'Market Highlights' pages.
Uses Playwright's shadow DOM support.
"""
from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel
from src.logger import get_logger

log = get_logger(__name__)

class PatternExtraction(BaseModel):
    symbol: str
    coin: str
    pattern_name: str
    interval: str = "N/A"
    status: str = "N/A"
    raw_text: str
    image_url: str
    is_locked: bool = False
    signal: str = "N/A"
    trend: str = "N/A"
    profit_potential: str = "N/A"
    price: str = "N/A"
    price_change: str = "N/A"
    category: str = "N/A"

def extract_patterns(page, source_type: str = "CHART_PATTERN") -> List[PatternExtraction]:
    """
    Finds trading pattern elements and extracts data using exact DOM targeting.
    """
    log.info("Extracting trading patterns from %s...", source_type)
    
    # Scroll down to load all cards
    try:
        page.evaluate("window.scrollBy(0, 500)")
        page.wait_for_timeout(2000)
        
        # Robust wait: ensure components are attached and have shadow roots with content
        page.evaluate('''() => {
            return new Promise(resolve => {
                let attempts = 0;
                const check = setInterval(() => {
                    const comps = document.querySelectorAll('altfins-trading-pattern-component');
                    let readyCount = 0;
                    comps.forEach(c => {
                        // A card is "ready" if it has a shadow root and either a description or a detail-row
                        if (c.shadowRoot) {
                            const hasContent = c.shadowRoot.querySelector('.detail-row-label') || 
                                               c.shadowRoot.querySelector('.description') ||
                                               c.shadowRoot.querySelector('.upgrade-unlock-container');
                            if (hasContent) readyCount++;
                        }
                    });
                    // Wait for at least 2 cards to be "ready" or timeout
                    if (readyCount >= 2 || attempts > 30) {
                        clearInterval(check);
                        resolve();
                    }
                    attempts++;
                }, 200);
            });
        }''')
    except Exception as e:
        log.warning("Wait loop interrupted: %s", e)

    # Extraction script with precise targeting
    extraction_script = """(sourceType) => {
        const results = [];
        
        // 1. Capture Global Interval
        let globalInterval = "N/A";
        const menuButtons = Array.from(document.querySelectorAll('vaadin-menu-bar-button, vaadin-menu-bar-item'));
        const activeInterval = menuButtons.find(btn => {
            const txt = btn.innerText.trim().toLowerCase();
            const isValidText = ["15m", "1h", "4h", "1d", "1w"].includes(txt);
            const isActive = btn.hasAttribute('highlight') || btn.hasAttribute('selected') || btn.getAttribute('aria-selected') === 'true';
            return isValidText && isActive;
        });
        
        if (activeInterval) {
            globalInterval = activeInterval.innerText.trim();
        } else {
            const fallback = menuButtons.find(btn => ["15m", "1h", "4h", "1d", "1w"].includes(btn.innerText.trim().toLowerCase()));
            if (fallback) globalInterval = fallback.innerText.trim();
        }

        // Default to 1D for Highlights page if nothing found
        if (globalInterval === "N/A" && window.location.href.includes("highlights")) {
            globalInterval = "1D";
        }

        // Helper to parse price/change from header text
        const parseHeader = (headerText) => {
            if (!headerText) return { price: "N/A", change: "N/A" };
            const lines = headerText.split('\\n').map(l => l.trim());
            let price = "N/A";
            let change = "N/A";
            
            for (const line of lines) {
                if (line.includes('$')) price = line;
                if (line.includes('%')) change = line;
            }
            
            // Fallback to regex if specific format not found
            if (price === "N/A") {
                const pMatch = headerText.match(/\\$\\s*([0-9.,]+)/);
                if (pMatch) price = pMatch[0].trim();
            }
            if (change === "N/A") {
                const cMatch = headerText.match(/([+-]?\\s*[0-9.,]+%)/);
                if (cMatch) change = cMatch[0].trim();
            }
            
            return { price, change };
        };

        // 2. Select Components
        let targetComponents = Array.from(document.querySelectorAll('altfins-trading-pattern-component'));
        
        // 3. Extract Patterns
        targetComponents.forEach(component => {
            const shadow = component.shadowRoot;
            if (!shadow) return;

            // Filter for Highlights page: only first row patterns
            if (sourceType === "MARKET_HIGHLIGHT") {
                const firstRow = document.querySelector('vaadin-board-row');
                if (firstRow && !firstRow.contains(component)) return;
            }

            // Check for Lock
            const isLockedLight = component.querySelector('altfins-chart-pattern-locked-img') !== null;
            const isLockedShadow = shadow.querySelector('altfins-chart-pattern-locked-img') !== null || 
                                   shadow.querySelector('.upgrade-unlock-container') !== null ||
                                   shadow.textContent.includes('Upgrade to unlock');
            
            const isLocked = isLockedLight || isLockedShadow;

            // Extract Header
            const widgetHeader = component.querySelector('widget-header');
            let symbol = "";
            let coin = "";
            let price = "N/A";
            let priceChange = "N/A";

            if (widgetHeader && widgetHeader.shadowRoot) {
                const primary = widgetHeader.shadowRoot.querySelector('#primary');
                const secondary = widgetHeader.shadowRoot.querySelector('#secondary');
                symbol = primary ? primary.innerText.trim() : "";
                coin = secondary ? secondary.innerText.trim() : "";
                
                const headerData = parseHeader(widgetHeader.shadowRoot.textContent);
                price = headerData.price;
                priceChange = headerData.change;
            }

            // Extract Details
            const getVal = (label) => {
                const rows = Array.from(shadow.querySelectorAll('.detail-row-label'));
                const target = rows.find(r => r.innerText.includes(label));
                return target ? target.parentElement.innerText.replace(label, "").trim() : "N/A";
            };

            const patternName = getVal('Pattern:');
            const signal = getVal('Signal:');
            const trend = getVal('Trend:');
            
            let cardInterval = getVal('Interval:');
            if (cardInterval === "N/A") cardInterval = globalInterval;

            const profitEl = shadow.querySelector('.profit-potential');
            let profitPotential = "N/A";
            if (profitEl) {
                const pText = profitEl.innerText;
                const pMatch = pText.match(/[+-]?\\s*[0-9.,]+%/);
                profitPotential = pMatch ? pMatch[0].trim() : "N/A";
            }

            const descEl = shadow.querySelector('span.description') || shadow.querySelector('[part="description"]');
            const rawText = descEl ? descEl.innerText.trim() : "N/A";
            const status = rawText.toLowerCase().includes("forming") ? "Forming" : "Completed";

            const img = shadow.querySelector('img.chart') || shadow.querySelector('.img-container img') || shadow.querySelector('img:not([src*="fullscreen"])');
            const imgSrc = img ? img.getAttribute('src') : "";

            results.push({
                type: "PATTERN",
                symbol,
                coin,
                pattern_name: patternName,
                signal,
                trend,
                profit_potential: profitPotential,
                status,
                interval: cardInterval,
                raw_text: rawText,
                img_src: imgSrc,
                is_locked: isLocked,
                price: price,
                price_change: priceChange
            });
        });

        // 4. Extract Market Data Components (Tables)
        if (sourceType === "MARKET_HIGHLIGHT") {
            const marketComps = Array.from(document.querySelectorAll('altfins-market-data-component'));
            marketComps.forEach(comp => {
                const shadow = comp.shadowRoot;
                const header = comp.querySelector('widget-header');
                if (!shadow || !header) return;

                const title = header.shadowRoot ? header.shadowRoot.textContent.trim().split('\\n')[0] : "Highlight";
                
                // Find grid and its rows
                // Vaadin grid rows are inside shadow root of vaadin-grid-table-body
                const grid = shadow.querySelector('vaadin-grid');
                if (!grid) return;

                // Extract data from rows
                // Since it's a headless run, we might need to rely on the cell values
                const rows = Array.from(grid.querySelectorAll('vaadin-grid-cell-content'));
                // Typically: Symbol, Name, Price, 24h Change
                // But we'll try to find symbols (usually uppercase, 3-5 chars)
                
                // Improved approach: extract by column if possible
                // For simplicity in this complex Vaadin environment, we'll try to find patterns in the text
                const text = grid.innerText;
                const cells = Array.from(grid.querySelectorAll('vaadin-grid-cell-content')).map(c => c.innerText.trim());
                
                // Group cells (usually 4-5 per row)
                // Let's look for Symbol/Price pairs
                for (let i = 0; i < cells.length; i++) {
                    const cell = cells[i];
                    // Symbol is usually first
                    if (cell && /^[A-Z0-9]{2,10}$/.test(cell) && cells[i+2] && cells[i+2].includes('$')) {
                        results.push({
                            type: "HIGHLIGHT",
                            category: title,
                            symbol: cell,
                            coin: cells[i+1] || cell,
                            price: cells[i+2],
                            price_change: cells[i+3] || "N/A",
                            pattern_name: "Market Highlight",
                            interval: globalInterval,
                            raw_text: `Market Highlight: ${title}`,
                            is_locked: false
                        });
                        i += 3; // skip processed row
                    }
                }
            });
        }

        return results;
    }"""

    try:
        data_list = page.evaluate(extraction_script, source_type)
    except Exception as e:
        log.error("Failed to evaluate extraction script: %s", e)
        return []

    results = []
    base_url = "https://altfins.com"

    for i, data in enumerate(data_list):
        symbol = data['symbol']
        if not symbol: continue
        
        # Skip locked cards if they have no pattern data
        if data['is_locked'] and data['pattern_name'] == "N/A":
            log.info("Skipping locked pattern card for %s", symbol)
            continue
            
        coin = data['coin'] or symbol
        log.info("Processing card %d: %s (%s) - Locked: %s", i + 1, coin, symbol, data['is_locked'])
        
        image_url = data['img_src']
        if image_url:
            if not image_url.startswith("http"):
                image_url = f"{base_url}{image_url if image_url.startswith('/') else '/' + image_url}"
        
        results.append(PatternExtraction(
            symbol=symbol,
            coin=coin,
            pattern_name=data['pattern_name'],
            interval=data['interval'],
            status=data['status'],
            raw_text=data['raw_text'],
            image_url=image_url or "",
            is_locked=data['is_locked'],
            signal=data['signal'],
            trend=data['trend'],
            profit_potential=data['profit_potential'],
            price=data['price'],
            price_change=data['price_change'],
            category=data.get('category', "N/A")
        ))
            
    log.info("Extracted %d valid patterns.", len(results))
    return results

