const fileSizeCache = new Map();

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    if (url.pathname === '/health') {
      const cookie = await env.DRIME_COOKIES.get('drime_cookie');
      return Response.json({
        status: 'ok',
        cookie_length: cookie ? cookie.length : 0,
        cookie_set: !!cookie,
      });
    }

    const proxyMatch = url.pathname.match(/^\/proxy\/([^/]+)\/([^/]+)\/(.+)$/);
    if (proxyMatch) {
      const [, hash, uuid, path] = proxyMatch;
      return this.proxySegment(hash, uuid, path, url.origin, env);
    }

    const masterMatch = url.pathname.match(/^\/master\/([^/]+)\/(.+)$/);
    if (masterMatch) {
      const [, uuid, path] = masterMatch;
      
      if (path.startsWith('audio_')) {
        return this.proxyAudio(uuid, path, url.origin, env);
      }
      
      const quality = path;
      return this.proxyMaster(uuid, quality, url.origin, env);
    }

    const directMatch = url.pathname.match(/^\/direct\/([^/]+)\/(\d+)\.mkv$/);
    if (directMatch) {
      const [, fileHash, shareableLinkId] = directMatch;
      return this.proxyDirect(request, fileHash, shareableLinkId, env, ctx);
    }

    const gdriveMatch = url.pathname.match(/^\/gdrive\/([^/]+)$/);
    if (gdriveMatch) {
      if (request.method === 'OPTIONS') {
        return new Response(null, {
          status: 204,
          headers: {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, OPTIONS',
            'Access-Control-Allow-Headers': 'Range',
            'Access-Control-Expose-Headers': 'Content-Range, Content-Length, Accept-Ranges',
            'Access-Control-Max-Age': '86400',
          },
        });
      }
      const [, fileId] = gdriveMatch;
      return this.proxyGoogleDrive(request, fileId, ctx);
    }

    return new Response('Not found', { status: 404 });
  },

  async proxyGoogleDrive(request, fileId, ctx) {
    const upstreamUrl = `https://drive.usercontent.google.com/download?id=${fileId}&export=download&confirm=t`;
    const ua = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36';
    const corsHeaders = {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Headers': 'Range',
      'Access-Control-Expose-Headers': 'Content-Range, Content-Length, Accept-Ranges',
    };

    const getOrProbeSize = async () => {
      if (fileSizeCache.has(fileId)) return fileSizeCache.get(fileId);
      const probe = await fetch(upstreamUrl, {
        headers: { 'User-Agent': ua, 'Range': 'bytes=0-0' },
      });
      if (probe.status !== 206) return null;
      const cr = probe.headers.get('Content-Range') || '';
      const total = parseInt(cr.split('/').pop() || '0', 10);
      if (total > 0) fileSizeCache.set(fileId, total);
      return total;
    };

    if (request.method === 'HEAD') {
      const total = await getOrProbeSize();
      if (!total) return new Response(null, { status: 503, headers: corsHeaders });
      return new Response(null, {
        status: 200,
        headers: {
          'Content-Type': 'video/x-matroska',
          'Content-Length': String(total),
          'Accept-Ranges': 'bytes',
          'Cache-Control': 'public, max-age=3600',
          ...corsHeaders,
        },
      });
    }

    const rangeHeader = request.headers.get('Range');
    let effectiveRange = rangeHeader || '';

    if (!rangeHeader || rangeHeader.match(/^bytes=\d+-$/)) {
      const total = await getOrProbeSize();
      if (!total) return Response.json({ error: 'File temporarily unavailable' }, { status: 503 });
      if (!rangeHeader) {
        effectiveRange = `bytes=0-${Math.min(total - 1, 16777215)}`;
      } else {
        const start = parseInt(rangeHeader.match(/^bytes=(\d+)/)?.[1] || '0', 10);
        effectiveRange = `bytes=${start}-${Math.min(total - 1, start + 16777215)}`;
      }
    }

    const cache = caches.default;
    const cacheKey = new Request(`${upstreamUrl}#${effectiveRange}`);
    const cached = await cache.match(cacheKey);
    if (cached) return cached;

    const upstream = await fetch(upstreamUrl, {
      headers: { 'User-Agent': ua, 'Range': effectiveRange },
    });

    if (!upstream.ok) {
      return Response.json({ error: `GDrive download failed: ${upstream.status}` }, { status: upstream.status });
    }

    const ct = upstream.headers.get('Content-Type') || '';
    if (ct.includes('text/html')) {
      return Response.json({ error: 'File temporarily unavailable' }, { status: 503 });
    }

    const response = new Response(upstream.body, {
      status: 206,
      headers: {
        'Content-Type': 'video/x-matroska',
        'Content-Range': upstream.headers.get('Content-Range') || '',
        'Content-Length': upstream.headers.get('Content-Length') || '',
        'Accept-Ranges': 'bytes',
        'Cache-Control': 'public, max-age=3600',
        ...corsHeaders,
      },
    });

    ctx.waitUntil(cache.put(cacheKey, response.clone()));
    return response;
  },

  async proxySegment(hash, uuid, path, workerBase, env) {
    const cookie = await env.DRIME_COOKIES.get('drime_cookie');
    if (!cookie) {
      return Response.json({ error: 'Cookie not set' }, { status: 503 });
    }

    const targetUrl = `https://stream.drime.cloud/${uuid}/${path}`;
    const upstream = await fetch(targetUrl, {
      headers: {
        Cookie: cookie,
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36',
        Referer: `https://app.drime.cloud/drive/s/${hash}`,
        'Accept': '*/*',
      },
    });

    if (!upstream.ok) {
      return Response.json({ error: 'Upstream failed', status: upstream.status, url: targetUrl }, { status: upstream.status });
    }

    const contentType = upstream.headers.get('content-type') || '';
    if (path.endsWith('.m3u8') || contentType.includes('mpegurl')) {
      const folder = path.replace('/video.m3u8', '').replace('/audio.m3u8', '');
      let body = await upstream.text();
      body = body.replace(/^(?!#)(.+)$/gm, (line) => {
        const trimmed = line.trim();
        if (!trimmed) return trimmed;
        if (trimmed.endsWith('.ts')) {
          return `${workerBase}/proxy/${hash || 'DUMMY'}/${uuid}/${folder}/${trimmed}`;
        }
        return trimmed;
      });
      return new Response(body, {
        headers: { 'Content-Type': 'application/vnd.apple.mpegurl', 'Access-Control-Allow-Origin': '*' },
      });
    }

    return new Response(upstream.body, {
      headers: { 'Content-Type': upstream.headers.get('content-type') || 'video/mp2t', 'Access-Control-Allow-Origin': '*' },
    });
  },

  async getDownloadUrl(fileHash, shareableLinkId, env, ctx) {
    const cache = caches.default;
    const cacheKey = `https://drime-cache.internal/download/${fileHash}/${shareableLinkId}`;

    const cached = await cache.match(cacheKey);
    if (cached) {
      return await cached.text();
    }

    const cookie = await env.DRIME_COOKIES.get('drime_cookie');
    if (!cookie) {
      throw new Error('Cookie not set');
    }

    const xsrfMatch = cookie.match(/XSRF-TOKEN=([^;]+)/);
    const xsrf = xsrfMatch ? decodeURIComponent(xsrfMatch[1]) : '';

    const targetUrl = `https://app.drime.cloud/api/v1/file-entries/download/${fileHash}?shareable_link=${shareableLinkId}`;

    const upstream = await fetch(targetUrl, {
      headers: {
        Cookie: cookie,
        'x-xsrf-token': xsrf,
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36',
        'Referer': 'https://app.drime.cloud/',
        'Accept': '*/*',
      },
    });

    if (!upstream.ok) {
      const text = await upstream.text();
      throw new Error(`Upstream failed: ${upstream.status} - ${text.slice(0, 200)}`);
    }

    const r2Url = upstream.headers.get('Location') || upstream.url;

    const cacheResponse = new Response(r2Url, {
      headers: {
        'Cache-Control': 's-maxage=1800, max-age=1800',
        'Content-Type': 'text/plain',
      },
    });
    ctx.waitUntil(cache.put(cacheKey, cacheResponse));

    return r2Url;
  },

  async proxyDirect(request, fileHash, shareableLinkId, env, ctx) {
    let downloadUrl;
    try {
      downloadUrl = await this.getDownloadUrl(fileHash, shareableLinkId, env, ctx);
    } catch (err) {
      return Response.json({ error: err.message }, { status: 503 });
    }

    const upstreamHeaders = {};
    const rangeHeader = request.headers.get('Range');
    if (rangeHeader) {
      upstreamHeaders['Range'] = rangeHeader;
    }

    const upstream = await fetch(downloadUrl, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36',
        'Accept': '*/*',
        'Referer': 'https://app.drime.cloud/',
        ...upstreamHeaders,
      },
    });

    const responseHeaders = {
      'Content-Type': upstream.headers.get('Content-Type') || 'video/x-matroska',
      'Accept-Ranges': 'bytes',
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Headers': 'Range',
      'Access-Control-Expose-Headers': 'Content-Range, Content-Length, Accept-Ranges',
    };

    if (upstream.headers.get('Content-Length')) {
      responseHeaders['Content-Length'] = upstream.headers.get('Content-Length');
    }
    if (upstream.headers.get('Content-Range')) {
      responseHeaders['Content-Range'] = upstream.headers.get('Content-Range');
    }

    return new Response(upstream.body, {
      status: upstream.status,
      headers: responseHeaders,
    });
  },

  async proxyMaster(uuid, quality, workerBase, env) {
    const cookie = await env.DRIME_COOKIES.get('drime_cookie');
    if (!cookie) {
      return Response.json({ error: 'Cookie not set' }, { status: 503 });
    }

    let targetUrl;
    const isQualityFolder = ['1080p', '720p', '480p', '360p', '240p'].includes(quality);
    
    if (quality === 'playlist.m3u8') {
      targetUrl = `https://stream.drime.cloud/${uuid}/playlist.m3u8`;
    } else if (isQualityFolder) {
      targetUrl = `https://stream.drime.cloud/${uuid}/playlist.m3u8`;
    } else if (quality.endsWith('/video.m3u8')) {
      const folder = quality.replace('/video.m3u8', '');
      targetUrl = `https://stream.drime.cloud/${uuid}/${folder}/video.m3u8`;
    } else {
      targetUrl = `https://stream.drime.cloud/${uuid}/${quality}/video.m3u8`;
    }

    const upstream = await fetch(targetUrl, {
      headers: {
        Cookie: cookie,
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36',
        Referer: 'https://app.drime.cloud/',
        'Accept': '*/*',
      },
    });

    if (!upstream.ok) {
      return Response.json({ error: 'Upstream failed', status: upstream.status, url: targetUrl }, { status: upstream.status });
    }

    let body = await upstream.text();
    
    if (isQualityFolder) {
      body = body.replace(/(audio_\d+\/audio\.m3u8)/g, (match) => {
        return `${workerBase}/master/${uuid}/${match}`;
      });
      body = body.replace(/^(?!#)(.+)$/gm, (line) => {
        const trimmed = line.trim();
        if (!trimmed) return trimmed;
        if (trimmed.endsWith('.m3u8')) {
          return `${workerBase}/master/${uuid}/${trimmed}`;
        }
        return trimmed;
      });
    } else if (quality.endsWith('/video.m3u8')) {
      const folder = quality.replace('/video.m3u8', '');
      body = body.replace(/^(?!#)(.+)$/gm, (line) => {
        const trimmed = line.trim();
        if (!trimmed) return trimmed;
        if (trimmed.endsWith('.ts')) {
          return `${workerBase}/proxy/DUMMY/${uuid}/${folder}/${trimmed}`;
        }
        return trimmed;
      });
    }

    return new Response(body, {
      headers: { 'Content-Type': 'application/vnd.apple.mpegurl', 'Access-Control-Allow-Origin': '*' },
    });
  },

  async proxyAudio(uuid, path, workerBase, env) {
    const cookie = await env.DRIME_COOKIES.get('drime_cookie');
    if (!cookie) {
      return Response.json({ error: 'Cookie not set' }, { status: 503 });
    }

    const targetUrl = `https://stream.drime.cloud/${uuid}/${path}`;
    const upstream = await fetch(targetUrl, {
      headers: {
        Cookie: cookie,
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
        Referer: 'https://app.drime.cloud/',
        'Accept': '*/*',
      },
    });

    if (!upstream.ok) {
      return Response.json({ error: 'Upstream failed', status: upstream.status, url: targetUrl }, { status: upstream.status });
    }

    let body = await upstream.text();
    const folder = path.replace('/audio.m3u8', '');
    body = body.replace(/^(?!#)(.+)$/gm, (line) => {
      const trimmed = line.trim();
      if (!trimmed) return trimmed;
      if (trimmed.endsWith('.ts')) {
        return `${workerBase}/proxy/AUDIO/${uuid}/${folder}/${trimmed}`;
      }
      return trimmed;
    });

    return new Response(body, {
      headers: { 'Content-Type': 'application/vnd.apple.mpegurl', 'Access-Control-Allow-Origin': '*' },
    });
  },
};
