# Discord Bot - Salas Temporales

Bot en Python usando Nextcord que crea salas de voz y texto temporales automáticamente y ofrece un sistema de selección de rango para jugadores de Dota 2.

## Características

- **Slash commands personalizados:**
  - `/setup`: Panel de ayuda con comandos principales.
  - `/yp generador <canal>`: Asigna el canal de voz que genera salas temporales.
  - `/yp rango`: Permite a los usuarios elegir su medalla de Dota 2 con botones e íconos.

- **Salas temporales:**
  - Al unirse al canal generador, se crea automáticamente una **categoría temporal** con:
    - Canal de voz `🎤-AUDIO` con límite de usuarios.
    - Canal de texto `💬-CHAT`.
  - Se eliminan automáticamente al quedar vacías.

- **Panel interactivo con botones** para asignar roles según medallas de Dota 2.

## Deploy 24/7 en Fly.io
- `Dockerfile` incluido para despliegue.
- Variables de entorno gestionadas con `flyctl secrets`.

## Probar el bot
Únete al servidor de Discord para probar todas las funciones del bot:  
👉 https://discord.gg/Ck4JdgWgQd
