/* ═══════════════════════════════════════════
   StockSense — charts.js
   Candlestick renderer + Chart.js helpers
═══════════════════════════════════════════ */

/**
 * Renders a candlestick chart into a container element.
 * @param {string} containerId  - ID of the .candle-chart div
 * @param {Array}  ohlcData     - [{open, high, low, close, date}, ...]
 */
function renderCandlestick(containerId, ohlcData) {
  const container = document.getElementById(containerId);
  if (!container || !ohlcData || ohlcData.length === 0) return;

  container.innerHTML = '';

  const CHART_H  = 110;   // pixel height of chart area
  const prices   = ohlcData.flatMap(c => [c.high, c.low]);
  const minP     = Math.min(...prices) * 0.999;
  const maxP     = Math.max(...prices) * 1.001;
  const range    = maxP - minP;

  // scale a price value to a pixel offset from top
  const scaleY = v => Math.round((1 - (v - minP) / range) * CHART_H);

  const dayLabels = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];

  ohlcData.forEach(candle => {
    const isUp   = candle.close >= candle.open;
    const color  = isUp ? '#10b981' : '#ef4444';
    const label  = candle.date
      ? dayLabels[new Date(candle.date).getDay()]
      : '';

    const hTop   = scaleY(candle.high);
    const lTop   = scaleY(candle.low);
    const wickH  = lTop - hTop;

    const bTop   = scaleY(Math.max(candle.open, candle.close));
    const bH     = Math.max(2, Math.abs(scaleY(candle.open) - scaleY(candle.close)));

    const col = document.createElement('div');
    col.className = 'candle-col';

    const wrap = document.createElement('div');
    wrap.className = 'candle-wrap';
    wrap.style.height = CHART_H + 'px';

    const wick = document.createElement('div');
    wick.className = 'candle-wick';
    wick.style.cssText = `top:${hTop}px; height:${wickH}px; background:${color};`;

    const body = document.createElement('div');
    body.className = 'candle-body';
    body.style.cssText = `top:${bTop}px; height:${bH}px; background:${color};`;

    wrap.appendChild(wick);
    wrap.appendChild(body);

    const lbl = document.createElement('div');
    lbl.className = 'candle-label';
    lbl.textContent = label;

    col.appendChild(wrap);
    col.appendChild(lbl);
    container.appendChild(col);
  });
}

/**
 * Renders a prediction line chart using Chart.js.
 * @param {string} canvasId     - ID of the <canvas> element
 * @param {Array}  historical   - [{date, price}, ...] past prices
 * @param {Array}  predicted    - [{date, price, upper, lower}, ...] forecast
 */
function renderPredictionChart(canvasId, historical, predicted) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;

  const histLabels = historical.map(d => d.date);
  const predLabels = predicted.map(d => d.date);
  const allLabels  = [...histLabels, ...predLabels.filter(l => !histLabels.includes(l))];

  const histPrices = allLabels.map(l => {
    const found = historical.find(d => d.date === l);
    return found ? found.price : null;
  });

  const predPrices = allLabels.map(l => {
    const found = predicted.find(d => d.date === l);
    return found ? found.price : null;
  });

  const predUpper = allLabels.map(l => {
    const found = predicted.find(d => d.date === l);
    return found ? found.upper : null;
  });

  const predLower = allLabels.map(l => {
    const found = predicted.find(d => d.date === l);
    return found ? found.lower : null;
  });

  if (window._predChart) window._predChart.destroy();

  window._predChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: allLabels,
      datasets: [
        {
          label: 'Historical price',
          data: histPrices,
          borderColor: '#6c47ff',
          borderWidth: 2,
          pointRadius: 2,
          pointBackgroundColor: '#6c47ff',
          tension: 0.3,
          fill: false,
          spanGaps: true,
        },
        {
          label: 'Predicted price',
          data: predPrices,
          borderColor: '#10b981',
          borderWidth: 2,
          borderDash: [5, 3],
          pointRadius: 3,
          pointBackgroundColor: '#10b981',
          tension: 0.3,
          fill: false,
          spanGaps: true,
        },
        {
          label: 'Upper bound',
          data: predUpper,
          borderColor: 'transparent',
          pointRadius: 0,
          fill: '+1',
          backgroundColor: 'rgba(16,185,129,0.08)',
          tension: 0.3,
          spanGaps: true,
        },
        {
          label: 'Lower bound',
          data: predLower,
          borderColor: 'rgba(16,185,129,0.25)',
          borderWidth: 0.5,
          pointRadius: 0,
          fill: false,
          tension: 0.3,
          spanGaps: true,
        },
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#fff',
          borderColor: '#e5e7eb',
          borderWidth: 1,
          titleColor: '#6b7280',
          bodyColor: '#374151',
          padding: 10,
          callbacks: {
            label: ctx => ctx.dataset.label + ': $' + (ctx.raw ? ctx.raw.toFixed(2) : 'N/A')
          }
        }
      },
      scales: {
        x: {
          grid: { color: '#f3f4f6' },
          ticks: {
            color: '#9ca3af',
            font: { family: "'DM Mono', monospace", size: 10 },
            maxTicksLimit: 8,
          }
        },
        y: {
          grid: { color: '#f3f4f6' },
          ticks: {
            color: '#9ca3af',
            font: { family: "'DM Mono', monospace", size: 10 },
            callback: v => '$' + v.toFixed(0)
          }
        }
      }
    }
  });
}
