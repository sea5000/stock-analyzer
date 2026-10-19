import React, { useState, useEffect } from 'react';
import {
  Upload,
  PlusCircle,
  RefreshCw,
  TrendingUp,
  TrendingDown,
  PieChart,
  ShieldAlert,
  Trash2,
  CheckCircle2,
  FileSpreadsheet
} from 'lucide-react';

interface Lot {
  lot_id: string;
  ticker: string;
  shares: number;
  buy_price: number;
  buy_date: string;
  account_type: string;
  notes?: string;
}

interface Position {
  ticker: string;
  total_shares: number;
  average_buy_price: number;
  total_cost: number;
  current_price: number;
  current_value: number;
  unrealized_pnl: number;
  unrealized_pnl_percent: string;
  portfolio_weight_percent: string;
  sector: string;
  industry: string;
  lot_count: number;
  lots: Lot[];
}

interface PortfolioReport {
  total_invested_cost: number;
  current_portfolio_value: number;
  total_unrealized_pnl: number;
  total_unrealized_pnl_percent: string;
  position_count: number;
  total_lot_count: number;
  positions: Position[];
  sector_breakdown: Record<string, { value: number; weight_percent: string; tickers: string[] }>;
  concentration_risk: {
    status: string;
    top_1_holding?: string;
    top_1_weight?: string;
    top_3_weight?: string;
  };
  last_updated?: string;
}

export const PortfolioView: React.FC = () => {
  const [report, setReport] = useState<PortfolioReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<string | null>(null);
  const [expandedTicker, setExpandedTicker] = useState<string | null>(null);

  // New Lot Form state
  const [showAddForm, setShowAddForm] = useState(false);
  const [newTicker, setNewTicker] = useState('');
  const [newShares, setNewShares] = useState('');
  const [newPrice, setNewPrice] = useState('');
  const [newDate, setNewDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [newAccount, setNewAccount] = useState('Taxable');

  const fetchPortfolio = async (force: boolean = false) => {
    if (!report) {
      setLoading(true);
    }
    setIsRefreshing(true);
    try {
      const url = force ? '/api/portfolio?force=true' : '/api/portfolio';
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        setReport(data);
      }
    } catch (err) {
      console.error("Failed to fetch portfolio:", err);
    } finally {
      setLoading(false);
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    fetchPortfolio();
  }, []);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploadStatus("Uploading & analyzing lots...");
    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch('/api/portfolio/upload', {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      if (res.ok) {
        setUploadStatus(`Success: Imported ${data.imported_count} lots!`);
        fetchPortfolio();
      } else {
        setUploadStatus(`Error: ${data.detail || "Upload failed"}`);
      }
    } catch (err: any) {
      setUploadStatus(`Upload failed: ${err.message}`);
    }
    setTimeout(() => setUploadStatus(null), 5000);
  };

  const handleResetSample = async () => {
    if (!confirm("Reset to default sample portfolio (NVDA, AAPL, MSFT, AMZN, JNJ, SPY)?")) return;
    try {
      await fetch('/api/portfolio/reset', { method: 'POST' });
      setUploadStatus("Loaded default sample portfolio.");
      fetchPortfolio(true);
    } catch (err) {
      console.error("Reset failed:", err);
      setUploadStatus("Failed to reset sample portfolio.");
    }
  };

  const handleClearPortfolio = async () => {
    if (!confirm("Are you sure you want to reset your portfolio and clear all holdings? All recorded stock lots will be permanently deleted.")) {
      return;
    }
    try {
      const res = await fetch('/api/portfolio/clear', { method: 'POST' });
      if (res.ok) {
        setUploadStatus("Portfolio cleared! All lots have been reset to empty.");
        fetchPortfolio(true);
      } else {
        setUploadStatus("Failed to clear portfolio.");
      }
    } catch (err) {
      console.error("Clear portfolio failed:", err);
      setUploadStatus("Failed to clear portfolio.");
    }
  };

  const handleAddLot = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTicker || !newShares || !newPrice) return;

    try {
      const res = await fetch('/api/portfolio/lot', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ticker: newTicker,
          shares: parseFloat(newShares),
          buy_price: parseFloat(newPrice),
          buy_date: newDate,
          account_type: newAccount
        })
      });
      if (res.ok) {
        setShowAddForm(false);
        setNewTicker('');
        setNewShares('');
        setNewPrice('');
        fetchPortfolio();
      }
    } catch (err) {
      console.error("Failed to add lot:", err);
    }
  };

  const handleDeleteLot = async (lotId: string) => {
    if (!confirm("Are you sure you want to delete this lot?")) return;
    try {
      await fetch(`/api/portfolio/lot/${lotId}`, { method: 'DELETE' });
      fetchPortfolio();
    } catch (err) {
      console.error("Failed to delete lot:", err);
    }
  };

  const isProfit = (report?.total_unrealized_pnl ?? 0) >= 0;

  return (
    <div className="portfolio-container">
      {/* Top Action Bar */}
      <div className="portfolio-header-bar">
        <div>
          <h2 className="section-title">Portfolio & Bought Lots Overview</h2>
          <p className="section-subtitle">Real-time valuation, cost basis tracking, and sector risk distribution.</p>
        </div>
        <div className="portfolio-actions">
          <label className="btn-secondary upload-label">
            <Upload size={16} /> Import CSV
            <input type="file" accept=".csv" onChange={handleFileUpload} style={{ display: 'none' }} />
          </label>
          <button className="btn-secondary" onClick={() => setShowAddForm(!showAddForm)}>
            <PlusCircle size={16} /> Add Lot
          </button>
          <button className="btn-secondary" onClick={handleResetSample} title="Load standard sample dataset (NVDA, AAPL, MSFT, etc.)">
            <FileSpreadsheet size={16} /> Sample Data
          </button>
          <button
            className="btn-danger"
            onClick={handleClearPortfolio}
            title="Reset and clear all lots in portfolio"
            disabled={!report?.positions || report.positions.length === 0}
          >
            <Trash2 size={16} /> Reset Portfolio
          </button>
          <button
            className="btn-secondary"
            onClick={() => fetchPortfolio(true)}
            title="Refresh live quotes"
            disabled={isRefreshing}
          >
            <RefreshCw size={16} className={isRefreshing ? "spin-icon" : ""} />
            {isRefreshing ? "Updating..." : "Refresh"}
          </button>
        </div>
      </div>

      {uploadStatus && (
        <div className="alert-banner">
          <CheckCircle2 size={16} /> {uploadStatus}
        </div>
      )}

      {/* Manual Lot Addition Form */}
      {showAddForm && (
        <form className="add-lot-form" onSubmit={handleAddLot}>
          <h3>Record New Bought Lot</h3>
          <div className="form-grid">
            <div className="form-group">
              <label>Ticker Symbol</label>
              <input placeholder="e.g. NVDA" value={newTicker} onChange={e => setNewTicker(e.target.value.toUpperCase())} required />
            </div>
            <div className="form-group">
              <label>Shares (Quantity)</label>
              <input type="number" step="any" placeholder="e.g. 15.0" value={newShares} onChange={e => setNewShares(e.target.value)} required />
            </div>
            <div className="form-group">
              <label>Cost Basis ($/share)</label>
              <input type="number" step="any" placeholder="e.g. 115.50" value={newPrice} onChange={e => setNewPrice(e.target.value)} required />
            </div>
            <div className="form-group">
              <label>Purchase Date</label>
              <input type="date" value={newDate} onChange={e => setNewDate(e.target.value)} required />
            </div>
            <div className="form-group">
              <label>Account</label>
              <select value={newAccount} onChange={e => setNewAccount(e.target.value)}>
                <option value="Taxable">Taxable</option>
                <option value="Roth IRA">Roth IRA</option>
                <option value="Traditional IRA">Traditional IRA</option>
                <option value="401k">401k</option>
              </select>
            </div>
          </div>
          <div className="form-buttons">
            <button type="submit" className="btn-primary">Save Lot</button>
            <button type="button" className="btn-secondary" onClick={() => setShowAddForm(false)}>Cancel</button>
          </div>
        </form>
      )}

      {/* Summary KPI Cards */}
      <div className="kpi-grid">
        <div className="kpi-card">
          <div className="kpi-label">Current Portfolio Value</div>
          <div className="kpi-value">${report?.current_portfolio_value?.toLocaleString('en-US', { minimumFractionDigits: 2 }) ?? '0.00'}</div>
          <div className="kpi-subtext">Total invested cost: ${report?.total_invested_cost?.toLocaleString('en-US', { minimumFractionDigits: 2 }) ?? '0.00'}</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-label">Total Unrealized P&L</div>
          <div className={`kpi-value ${isProfit ? 'text-profit' : 'text-loss'}`}>
            {isProfit ? '+' : ''}${report?.total_unrealized_pnl?.toLocaleString('en-US', { minimumFractionDigits: 2 }) ?? '0.00'}
          </div>
          <div className={`kpi-badge ${isProfit ? 'badge-profit' : 'badge-loss'}`}>
            {isProfit ? <TrendingUp size={14} /> : <TrendingDown size={14} />} {report?.total_unrealized_pnl_percent ?? '0.00%'}
          </div>
        </div>

        <div className="kpi-card">
          <div className="kpi-label">Holdings & Lots</div>
          <div className="kpi-value">{report?.position_count ?? 0} Stocks</div>
          <div className="kpi-subtext">{report?.total_lot_count ?? 0} total purchase lots recorded</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-label">Concentration Risk</div>
          <div className="kpi-value status-indicator">
            <ShieldAlert size={20} className="alert-icon" />
            <span className="risk-text">{report?.concentration_risk?.status || "Analyzing..."}</span>
          </div>
          <div className="kpi-subtext">
            Top 3 Holdings: {report?.concentration_risk?.top_3_weight ?? '0%'}
          </div>
        </div>
      </div>

      {/* Sector Allocation Breakdown */}
      {report?.sector_breakdown && Object.keys(report.sector_breakdown).length > 0 && (
        <div className="sector-breakdown-card">
          <h3 className="card-heading">
            <PieChart size={18} /> Sector Diversification Exposure
          </h3>
          <div className="sector-bars">
            {Object.entries(report.sector_breakdown).map(([sector, data]) => {
              const pct = parseFloat(data.weight_percent.replace('%', ''));
              return (
                <div key={sector} className="sector-item">
                  <div className="sector-header">
                    <span className="sector-name">{sector}</span>
                    <span className="sector-pct">{data.weight_percent} (${data.value.toLocaleString()})</span>
                  </div>
                  <div className="progress-track">
                    <div className="progress-fill" style={{ width: `${Math.min(pct, 100)}%` }} />
                  </div>
                  <div className="sector-tickers">Tickers: {data.tickers.join(', ')}</div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Positions and Lots Table */}
      <div className="positions-table-card">
        <h3 className="card-heading">Holdings & Bought Lots Breakdown</h3>
        <div className="table-wrapper">
          <table className="positions-table">
            <thead>
              <tr>
                <th>Ticker</th>
                <th>Sector</th>
                <th>Shares</th>
                <th>Avg Cost</th>
                <th>Current Price</th>
                <th>Position Value</th>
                <th>Unrealized P&L</th>
                <th>Weight</th>
                <th>Lots</th>
              </tr>
            </thead>
            <tbody>
              {report?.positions && report.positions.length > 0 ? (
                report.positions.map((pos) => {
                  const posProfit = pos.unrealized_pnl >= 0;
                  const isExpanded = expandedTicker === pos.ticker;
                  return (
                    <React.Fragment key={pos.ticker}>
                      <tr className="position-row" onClick={() => setExpandedTicker(isExpanded ? null : pos.ticker)}>
                        <td className="ticker-cell">
                          <strong>{pos.ticker}</strong>
                        </td>
                        <td>{pos.sector}</td>
                        <td>{pos.total_shares}</td>
                        <td>${pos.average_buy_price.toFixed(2)}</td>
                        <td>${pos.current_price.toFixed(2)}</td>
                        <td>${pos.current_value.toLocaleString('en-US', { minimumFractionDigits: 2 })}</td>
                        <td className={posProfit ? 'text-profit' : 'text-loss'}>
                          {posProfit ? '+' : ''}${pos.unrealized_pnl.toLocaleString('en-US', { minimumFractionDigits: 2 })} ({pos.unrealized_pnl_percent})
                        </td>
                        <td>{pos.portfolio_weight_percent}</td>
                        <td>
                          <button className="expand-pill">
                            {pos.lot_count} lots {isExpanded ? '▲' : '▼'}
                          </button>
                        </td>
                      </tr>
                      {/* Expanded Lots Sub-table */}
                      {isExpanded && (
                        <tr className="expanded-lots-row">
                          <td colSpan={9}>
                            <div className="lots-detail-panel">
                              <h4>Purchase Lots for {pos.ticker}</h4>
                              <table className="lots-subtable">
                                <thead>
                                  <tr>
                                    <th>Date</th>
                                    <th>Shares</th>
                                    <th>Buy Price</th>
                                    <th>Lot Cost</th>
                                    <th>Account</th>
                                    <th>Notes</th>
                                    <th>Action</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {pos.lots.map(lot => (
                                    <tr key={lot.lot_id}>
                                      <td>{lot.buy_date}</td>
                                      <td>{lot.shares}</td>
                                      <td>${lot.buy_price.toFixed(2)}</td>
                                      <td>${(lot.shares * lot.buy_price).toFixed(2)}</td>
                                      <td>{lot.account_type}</td>
                                      <td>{lot.notes || '-'}</td>
                                      <td>
                                        <button className="btn-delete" onClick={() => handleDeleteLot(lot.lot_id)} title="Delete Lot">
                                          <Trash2 size={14} />
                                        </button>
                                      </td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })
              ) : (
                <tr>
                  <td colSpan={9} className="empty-row">
                    {loading ? (
                      <div className="empty-state-content">
                        <RefreshCw size={24} className="spin-icon" />
                        <p>Loading portfolio and real-time market quotes...</p>
                      </div>
                    ) : (
                      <div className="empty-state-content">
                        <p className="empty-state-title">Your portfolio is currently empty</p>
                        <p className="empty-state-desc">
                          You can import a brokerage CSV, record individual bought lots, or load the pre-configured sample portfolio to explore analytics.
                        </p>
                        <div className="empty-state-actions">
                          <button className="btn-primary" onClick={handleResetSample}>
                            <FileSpreadsheet size={15} /> Load Sample Portfolio
                          </button>
                          <button className="btn-secondary" onClick={() => setShowAddForm(true)}>
                            <PlusCircle size={15} /> Add First Lot
                          </button>
                          <label className="btn-secondary upload-label">
                            <Upload size={15} /> Import CSV
                            <input type="file" accept=".csv" onChange={handleFileUpload} style={{ display: 'none' }} />
                          </label>
                        </div>
                      </div>
                    )}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
