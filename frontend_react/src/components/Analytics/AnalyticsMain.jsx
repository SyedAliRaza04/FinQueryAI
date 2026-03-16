import React, { useState, useEffect } from 'react';
import { RefreshCw, Download, DollarSign, Users, Briefcase, Activity } from 'lucide-react';
import './AnalyticsMain.css';

const API_BASE_URL = "http://localhost:8000/api";

const AnalyticsMain = () => {
  const [isRefreshing, setIsRefreshing] = useState(false);
  
  // Real data state
  const [data, setData] = useState({
     totalAssets: "$0.0M",
     activeUsers: "0",
     activeLoans: "0",
     monthlyTx: "$0.0M",
     chartData: [0, 0, 0, 0, 0, 0, 0], // Heights in percentage
     topPortfolios: []
  });

  useEffect(() => {
     fetchAnalytics();
  }, []);

  const fetchAnalytics = async () => {
       setIsRefreshing(true);
       try {
           const res = await fetch(`${API_BASE_URL}/analytics/`, {
               headers: {
                   'Authorization': `Bearer ${localStorage.getItem('fq-token')}`,
                   'Content-Type': 'application/json'
               }
           });
           const newData = await res.json();
           if (res.ok) {
               setData(newData);
           } else {
               console.error("Failed to fetch analytics:", newData.error);
           }
       } catch (err) {
           console.error("Network error fetching analytics:", err);
       } finally {
           setIsRefreshing(false);
       }
   };

  const handleRefresh = () => {
     fetchAnalytics();
  };

  return (
    <div className="analytics-main-container">
      <div className="dashboard-header">
        <div className="dashboard-title">
          <h2>Portfolio Overview</h2>
          <p>Live analysis drawn from current database queries</p>
        </div>
        <div className="dashboard-actions">
          <button className="primary-btn" onClick={handleRefresh}>
             <RefreshCw size={16} className={isRefreshing ? 'animate-spin' : ''} />
             {isRefreshing ? 'Syncing...' : 'Live Update'}
          </button>
          <button className="icon-btn" style={{border: '1px solid rgba(255,255,255,0.1)'}}>
             <Download size={18} />
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="kpi-grid">
         <div className="kpi-card">
            <div className="kpi-header">
               <span>Total Managed Assets</span>
               <DollarSign size={18} className="text-yellow" />
            </div>
            <div className="kpi-value">{data.totalAssets}</div>
            <div className="kpi-trend trend-up">↑ 4.2% from last month</div>
         </div>
         
         <div className="kpi-card">
            <div className="kpi-header">
               <span>Active Customers</span>
               <Users size={18} className="text-blue" />
            </div>
            <div className="kpi-value">{data.activeUsers}</div>
            <div className="kpi-trend trend-up">↑ 1.1% from last month</div>
         </div>
         
         <div className="kpi-card">
            <div className="kpi-header">
               <span>Active Loans</span>
               <Briefcase size={18} className="text-purple" />
            </div>
            <div className="kpi-value">{data.activeLoans}</div>
            <div className="kpi-trend trend-down">↓ 0.5% from last month</div>
         </div>
         
         <div className="kpi-card">
            <div className="kpi-header">
               <span>Monthly Transacted</span>
               <Activity size={18} className="text-green" />
            </div>
            <div className="kpi-value">{data.monthlyTx}</div>
            <div className="kpi-trend trend-up">↑ 12.4% from last month</div>
         </div>
      </div>

      {/* Charts Section */}
      <div className="charts-grid">
         {/* Main Chart */}
         <div className="chart-card">
            <div className="chart-header">
               <h3>Transaction Volume (Last 7 Months)</h3>
            </div>
            <div className="css-bar-chart">
               {data.chartData.map((height, i) => (
                  <div key={i} className="bar-wrapper">
                     <div className="bar" style={{height: `${height}%`}}></div>
                     <span>{['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul'][i]}</span>
                  </div>
               ))}
            </div>
         </div>

         {/* List Widget */}
         <div className="chart-card">
            <div className="chart-header">
               <h3>Top Portfolios</h3>
            </div>
            <div className="data-list">
               {data.topPortfolios.map((item, idx) => (
                  <div key={idx} className="data-list-item">
                     <div className="list-item-left">
                        <div className="item-icon">📂</div>
                        <div className="item-info">
                           <h4>{item.name}</h4>
                           <p>{item.type}</p>
                        </div>
                     </div>
                     <div className="list-item-right">
                        <div className="amount">{item.amount}</div>
                        <div className={`rate ${item.ror.startsWith('+') ? 'trend-up' : 'trend-down'}`}>
                           {item.ror}
                        </div>
                     </div>
                  </div>
               ))}
            </div>
         </div>
      </div>
    </div>
  );
};

export default AnalyticsMain;
