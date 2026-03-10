export default {
  async fetch(request, env) {
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

    return new Response('Not found', { status: 404 });
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
