export function malformedUriGuard() {
  return {
    name: 'nexus-malformed-uri-guard',
    configureServer(server) {
      server.middlewares.use((request, response, next) => {
        try {
          decodeURI(request.url || '/')
          next()
        } catch {
          response.statusCode = 400
          response.setHeader('Content-Type', 'text/plain; charset=utf-8')
          response.end('Bad Request')
        }
      })
    },
  }
}
