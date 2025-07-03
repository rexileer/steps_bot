(() => {
  const tg = window.Telegram?.WebApp ?? null
  tg?.expand()

  const walkType =
    new URLSearchParams(location.search).get('walk_type') || 'dog'

  const icon = L.icon({
    iconUrl: {
      dog: '/static/markers/dog.png',
      stroller: '/static/markers/stroller.png',
      both: '/static/markers/both.png',
    }[walkType],
    iconSize: [50, 50],
    iconAnchor: [20, 40],
    popupAnchor: [0, -40],
  })

  let map,
    marker,
    initialized = false,
    tracking = false,
    distance = 0,
    path = []

  const ACC_LIMIT = 60,
    MIN_MOVE = 3,
    STEP_LEN = 0.7

  const toRad = (v) => (v * Math.PI) / 180
  const hav = (a, b, c, d) => {
    const R = 6_371_000
    const dLat = toRad(c - a)
    const dLon = toRad(d - b)
    const k =
      Math.sin(dLat / 2) ** 2 +
      Math.cos(toRad(a)) * Math.cos(toRad(c)) * Math.sin(dLon / 2) ** 2
    return R * 2 * Math.atan2(Math.sqrt(k), Math.sqrt(1 - k))
  }

  const $ = (id) => document.getElementById(id)
  const stat = (t) => ($('status').textContent = t)
  const upd = () => {
    const s = Math.round(distance / STEP_LEN);
    $('steps').textContent = s;
    $('points').textContent = s;

    const elapsed = (Date.now() - startTime) / 1000; // секунд
    const kmh = elapsed > 10 ? (distance / elapsed) * 3.6 : 0;
    $('speed').textContent = kmh.toFixed(1);
  };

  const fix = (lat, lng, acc) => {
    if (!initialized) {
      map = L.map('map').setView([lat, lng], 17)
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(
        map
      )
      marker = L.marker([lat, lng], { icon })
        .addTo(map)
        .bindPopup('Вы здесь')
        .openPopup()
      initialized = true
    } else {
      marker.setLatLng([lat, lng])
      map.setView([lat, lng])
    }

    if (acc > ACC_LIMIT) return stat(`GPS: ~${Math.round(acc)} м`)

    const last = path.at(-1)
    if (last) {
      const d = hav(last.lat, last.lng, lat, lng)
      if (d > MIN_MOVE && d < 200) {
        distance += d
        upd()
      }
    }
    path.push({ lat, lng, ts: Date.now() })
    stat(`GPS: ${Math.round(acc)} м`)
  }

  const startTracking = async () => {
    if (tracking) return
    tracking = true

    if (tg?.LocationManager?.mount) {
      try {
        await tg.LocationManager.mount()
      } catch {

      }

      tg.onEvent('locationManagerUpdated', (l) => {
        if (l?.available)
          fix(l.latitude, l.longitude, l.horizontal_accuracy || 0)
      })

      try {
        const l = await tg.LocationManager.requestLocation()
        if (l?.available)
          fix(l.latitude, l.longitude, l.horizontal_accuracy || 0)
      } catch {
        stat('Не удалось получить геопозицию')
      }
      return
    }

    navigator.geolocation.watchPosition(
      (p) =>
        fix(p.coords.latitude, p.coords.longitude, p.coords.accuracy || 0),
      (e) => stat('Ошибка: ' + e.message),
      { enableHighAccuracy: true, maximumAge: 0, timeout: 10_000 }
    )
  }

    ; (() => {
      const btnStart = $('start')
      if (btnStart) {
        btnStart.addEventListener('click', async () => {
          if (tg?.LocationManager?.openSettings)
            await tg.LocationManager.openSettings()
          await startTracking()
          btnStart.remove()
        })
      } else startTracking()
    })()

  $('finish').addEventListener('click', () => {
    tg?.sendData(
      JSON.stringify({
        walk_type: walkType,
        steps: Math.round(distance / STEP_LEN),
        distance: Math.round(distance),
        coords: path,
      })
    )
    tg?.close()
  })
})()
