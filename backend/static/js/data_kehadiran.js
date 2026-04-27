// let evtSource = null;

// window.addEventListener("DOMContentLoaded", () => {
//   const filterInput = document.getElementById('filter-date');
//   const saved = sessionStorage.getItem('kehadiran_filter_date');

//   filterInput.value = saved || getToday();

//   startSSE();
// });


// // ================================
// // START SSE
// // ================================
// function startSSE() {
//   const keyword = document.getElementById('search').value.trim();
//   const tanggal = document.getElementById('filter-date').value;

//   // tutup koneksi lama
//   if (evtSource) {
//     evtSource.close();
//   }

//   const url = `/kehadiran/stream?keyword=${encodeURIComponent(keyword)}&tanggal=${tanggal}`;
//   evtSource = new EventSource(url);

//   evtSource.onmessage = function(event) {
//     const data = JSON.parse(event.data);

//     if (data.error) {
//       console.error("Error:", data.error);
//       return;
//     }

//     renderTable(data);
//   };

//   evtSource.onerror = function() {
//     console.log("SSE error, reconnecting...");
//     evtSource.close();

//     setTimeout(() => {
//       startSSE();
//     }, 3000);
//   };
// }


// // ================================
// // RENDER TABLE
// // ================================
// function renderTable(data) {
//   const tbody = document.getElementById('tbody');

//   document.getElementById('total-badge').textContent = `${data.length} data`;

//   if (data.length === 0) {
//     tbody.innerHTML = `
//       <tr><td colspan="4">
//         <div class="empty">Tidak ada data kehadiran</div>
//       </td></tr>`;
//     return;
//   }

//   tbody.innerHTML = data.map(row => `
//     <tr>
//       <td class="nim">${row.nim}</td>
//       <td class="nama">${row.nama}</td>
//       <td class="waktu">${row.waktu_absen}</td>
//       <td><span class="badge-hadir">${row.status}</span></td>
//     </tr>
//   `).join('');
// }


// // ================================
// // FILTER & SEARCH
// // ================================
// function onDateChange() {
//   const val = document.getElementById('filter-date').value;
//   sessionStorage.setItem('kehadiran_filter_date', val);

//   startSSE(); // restart stream
// }

// function onSearch() {
//   startSSE(); // restart stream
// }


// // ================================
// // UTIL
// // ================================
// function getToday() {
//   return new Date().toLocaleDateString('sv-SE');
// }


// ================================
// GANTI SELURUH JS DENGAN INI
// ================================

let refreshInterval = null;

window.addEventListener("DOMContentLoaded", () => {
  const filterInput = document.getElementById('filter-date');
  const saved = sessionStorage.getItem('kehadiran_filter_date');
  filterInput.value = saved || getToday();

  fetchData(); // load pertama
  startAutoRefresh(); // mulai auto refresh
});


// ================================
// FETCH DATA (SIMPLE & CEPAT)
// ================================
async function fetchData() {
  const keyword = document.getElementById('search').value.trim();
  const tanggal = document.getElementById('filter-date').value;
  

  const url = `/kehadiran/data?keyword=${encodeURIComponent(keyword)}&tanggal=${tanggal}`;

  try {
    const res = await fetch(url);
    const data = await res.json();

    if (data.error) {
      console.error("Error:", data.error);
      return;
    }

    renderTable(data);
  } catch (err) {
    console.error("Fetch error:", err);
  }
}


// ================================
// AUTO REFRESH TIAP 10 DETIK
// ================================
function startAutoRefresh() {
  if (refreshInterval) clearInterval(refreshInterval);
  refreshInterval = setInterval(fetchData, 10000); // tiap 10 detik
}


// ================================
// FILTER & SEARCH
// ================================
function onDateChange() {
  const val = document.getElementById('filter-date').value;
  sessionStorage.setItem('kehadiran_filter_date', val);

  fetchData(); // langsung fetch, tidak perlu restart stream
}

function onSearch() {
  fetchData();
}


// ================================
// RENDER TABLE (sama seperti sebelumnya)
// ================================
function renderTable(data) {
  const tbody = document.getElementById('tbody');
  document.getElementById('total-badge').textContent = `${data.length} data`;

  if (data.length === 0) {
    tbody.innerHTML = `
      <tr><td colspan="4">
        <div class="empty">Tidak ada data kehadiran</div>
      </td></tr>`;
    return;
  }

  tbody.innerHTML = data.map(row => `
    <tr>
      <td class="nim">${row.nim}</td>
      <td class="nama">${row.nama}</td>
      <td class="waktu">${row.waktu_absen}</td>
      <td><span class="badge-hadir">${row.status}</span></td>
    </tr>
  `).join('');
}


// ================================
// UTIL
// ================================
function getToday() {
  return new Date().toLocaleDateString('sv-SE');
}