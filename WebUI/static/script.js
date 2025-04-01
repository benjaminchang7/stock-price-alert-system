// Proxy Endpoints
const portfolioServiceUrl = '/api/portfolio';
const triggeredAlertServiceUrl = '/api/alerts';
const alertConditionServiceUrl = '/api/alert';

// Portfolio Management functions
function loadPortfolios() {
  const userId = document.getElementById('user_id').value;
  let url = portfolioServiceUrl;
  if (userId) {
    url += '?user_id=' + encodeURIComponent(userId);
  }
  fetch(url)
    .then(response => response.json())
    .then(data => {
      const tbody = document.querySelector('#portfolio-table tbody');
      tbody.innerHTML = '';
      data.forEach(item => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td>${item.user_id}</td>
          <td>${item.stock_symbol}</td>
          <td>${item.quantity}</td>
          <td>${item.current_price !== undefined ? item.current_price : 'N/A'}</td>
          <td>
            <button onclick="editPortfolio('${item.portfolio_id}', '${item.user_id}', '${item.stock_symbol}', ${item.quantity})">Edit</button>
            <button onclick="deletePortfolio('${item.portfolio_id}')">Delete</button>
          </td>
        `;
        tbody.appendChild(tr);
      });
    })
    .catch(err => console.error('Error loading portfolios:', err));
}

function editPortfolio(id, user_id, stock_symbol, quantity) {
  document.getElementById('portfolio_id').value = id;
  document.getElementById('user_id').value = user_id;
  document.getElementById('stock_symbol').value = stock_symbol;
  document.getElementById('quantity').value = quantity;
}

function deletePortfolio(id) {
  fetch(portfolioServiceUrl + '?portfolio_id=' + encodeURIComponent(id), { method: 'DELETE' })
    .then(response => response.json())
    .then(data => {
      alert(data.message);
      loadPortfolios();
    })
    .catch(err => console.error('Error deleting portfolio:', err));
}

document.getElementById('portfolio-form').addEventListener('submit', function(e) {
  e.preventDefault();
  const portfolioId = document.getElementById('portfolio_id').value;
  const user_id = document.getElementById('user_id').value;
  const stock_symbol = document.getElementById('stock_symbol').value;
  const quantity = parseInt(document.getElementById('quantity').value);
  const payload = { user_id, stock_symbol, quantity };

  if (portfolioId) {
    fetch(portfolioServiceUrl + '?portfolio_id=' + encodeURIComponent(portfolioId), {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
      .then(response => response.json())
      .then(data => {
        alert(data.message);
        document.getElementById('portfolio-form').reset();
        loadPortfolios();
      })
      .catch(err => console.error('Error updating portfolio:', err));
  } else {
    fetch(portfolioServiceUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
      .then(response => response.json())
      .then(data => {
        alert(data.message);
        document.getElementById('portfolio-form').reset();
        loadPortfolios();
      })
      .catch(err => console.error('Error adding portfolio:', err));
  }
});

// Triggered Alerts (Alert Management Service)
function loadAlerts() {
  fetch(triggeredAlertServiceUrl)
    .then(response => response.json())
    .then(data => {
      const container = document.getElementById('alerts-container');
      container.innerHTML = '';
      data.forEach(alert => {
        const div = document.createElement('div');
        div.className = 'alert-box';
        div.innerHTML = `
          <span class="close" onclick="this.parentElement.remove();">&times;</span>
          <strong>Alert!</strong> ${alert.stock_symbol} is ${alert.condition} ${alert.threshold}. Current price: ${alert.price}
        `;
        container.appendChild(div);
      });
    })
    .catch(err => console.error('Error loading alerts:', err));
}

// Alert Conditions
function loadAlertConditions() {
  fetch(alertConditionServiceUrl)
    .then(response => response.json())
    .then(data => {
      const tbody = document.querySelector('#alert-table tbody');
      tbody.innerHTML = '';
      data.forEach(item => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td>${item.alert_id}</td>
          <td>${item.stock_symbol}</td>
          <td>${item.condition_type}</td>
          <td>${item.threshold}</td>
          <td>
            <button onclick="deleteAlertCondition('${item.alert_id}')">Delete</button>
          </td>
        `;
        tbody.appendChild(tr);
      });
    })
    .catch(err => console.error('Error loading alert conditions:', err));
}

document.getElementById('alert-form').addEventListener('submit', function(e) {
  e.preventDefault();
  const alert_id = document.getElementById('alert_id').value;
  const stock_symbol = document.getElementById('alert_stock_symbol').value;
  const condition_type = document.getElementById('condition_type').value;
  const threshold = parseFloat(document.getElementById('threshold').value);
  const payload = { alert_id, stock_symbol, condition_type, threshold };
  fetch(alertConditionServiceUrl, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
    .then(response => response.json())
    .then(data => {
      alert(data.message);
      document.getElementById('alert-form').reset();
      loadAlertConditions();
    })
    .catch(err => console.error('Error adding alert condition:', err));
});

function deleteAlertCondition(alert_id) {
  fetch(alertConditionServiceUrl + '?alert_id=' + encodeURIComponent(alert_id), {
    method: 'DELETE'
  })
    .then(response => response.json())
    .then(data => {
      alert(data.message);
      loadAlertConditions();
    })
    .catch(err => console.error('Error deleting alert condition:', err));
}

// Load and Periodic Refresh
document.addEventListener('DOMContentLoaded', function() {
  loadPortfolios();
  loadAlerts();
  loadAlertConditions();
  setInterval(loadAlerts, 10000);
});