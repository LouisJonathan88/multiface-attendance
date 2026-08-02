window.addEventListener("DOMContentLoaded", () => {
  const filterDari = document.getElementById('filter-date-dari');
  const filterSampai = document.getElementById('filter-date-sampai');

  // Ambil state terakhir atau gunakan default hari ini
  filterDari.value = sessionStorage.getItem('kehadiran_filter_dari') || getToday();
  filterSampai.value = sessionStorage.getItem('kehadiran_filter_sampai') || getToday();

  muatDataKehadiran();
});

// ================================
// AMBIL DATA
// ================================
function muatDataKehadiran() {
  const keyword = document.getElementById('search').value.trim();
  const tglDari = document.getElementById('filter-date-dari').value;
  const tglSampai = document.getElementById('filter-date-sampai').value;

  const url = `/kehadiran/data?keyword=${encodeURIComponent(keyword)}&tanggal_dari=${tglDari}&tanggal_sampai=${tglSampai}`;

  fetch(url)
    .then(response => response.json())
    .then(data => {
      renderTable(data, keyword, tglDari, tglSampai);
    })
    .catch(err => {
      console.error("Gagal memuat data kehadiran:", err);
      tampilkanNotifikasi("Gagal memuat data kehadiran. Coba muat ulang halaman.", "error");
    });
}

// ================================
// FILTER & SEARCH
// ================================
function onDateChange() {
  const tglDari = document.getElementById('filter-date-dari').value;
  const tglSampai = document.getElementById('filter-date-sampai').value;

  // Skenario: Validasi Tanggal Terbalik
  if (tglDari && tglSampai && tglDari > tglSampai) {
    tampilkanNotifikasi("Rentang tanggal tidak valid: 'Tanggal Dari' tidak boleh melewati 'Tanggal Sampai'.", "error");
    return; // Berhenti di sini, jangan fetch data
  }

  sessionStorage.setItem('kehadiran_filter_dari', tglDari);
  sessionStorage.setItem('kehadiran_filter_sampai', tglSampai);
  muatDataKehadiran();
}

function onSearch() {
  muatDataKehadiran();
}

// ================================
// EXPORT EXCEL
// ================================
function exportExcel() {
  const keyword = document.getElementById('search').value.trim();
  const tglDari = document.getElementById('filter-date-dari').value;
  const tglSampai = document.getElementById('filter-date-sampai').value;

  if (tglDari && tglSampai && tglDari > tglSampai) {
    tampilkanNotifikasi("Perbaiki rentang tanggal terlebih dahulu sebelum melakukan export.", "error");
    return;
  }

  const url = `/kehadiran/export?keyword=${encodeURIComponent(keyword)}&tanggal_dari=${tglDari}&tanggal_sampai=${tglSampai}`;

  tampilkanNotifikasi("Menyiapkan file Excel...", "info");

  fetch(url)
    .then(response => {
      if (!response.ok) {
        throw new Error("Gagal mengekspor data");
      }
      return response.blob();
    })
    .then(blob => {
      const downloadUrl = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = downloadUrl;
      a.download = `Presensi_${tglDari || 'semua'}_sd_${tglSampai || 'data'}.xlsx`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(downloadUrl);

      tampilkanNotifikasi("Data kehadiran berhasil diekspor.", "success");
    })
    .catch(err => {
      console.error("Export error:", err);
      tampilkanNotifikasi("Tidak ada data yang dapat diekspor atau terjadi kesalahan.", "error");
    });
}

// ================================
// NOTIFIKASI
// ================================
function tampilkanNotifikasi(pesan, tipe = "info") {
  let notif = document.getElementById('notif-toast');
  if (!notif) {
    notif = document.createElement('div');
    notif.id = 'notif-toast';
    document.body.appendChild(notif);
  }

  notif.textContent = pesan;
  notif.className = `notif-toast notif-${tipe} show`;

  clearTimeout(notif._timeoutId);
  notif._timeoutId = setTimeout(() => {
    notif.classList.remove('show');
  }, 3000);
}

// ================================
// RENDER TABLE
// ================================
function renderTable(data, keyword = "", tglDari = "", tglSampai = "") {
  const tbody = document.getElementById('tbody');
  document.getElementById('total-badge').textContent = `${data.length} data`;

  if (data.length === 0) {
    let pesan = "Data tidak ditemukan";
    // Jika tidak ada filter yang dipakai sama sekali, pesan menyesuaikan
    if (!keyword && !tglDari && !tglSampai) {
      pesan = "Data kehadiran belum tersedia";
    }
    tbody.innerHTML = `<tr><td colspan="4"><div class="empty" style="text-align: center; padding: 20px;">${pesan}</div></td></tr>`;
    return;
  }

  tbody.innerHTML = data.map(row => `
    <tr>
      <td class="nomor-identitas">${row.nomor_identitas}</td>
      <td class="nama">${row.nama}</td>
      <td class="waktu">${row.waktu_presensi}</td>
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