# Paso 9d: SARIMAX con el día de la semana como variable explicativa, y el horizonte h = 10.
#
#     Rscript 9d_sarimax_dia_semana.R
#
# Revisión del 26 de noviembre de 2026. El SARIMAX de la tesis (5_modelo_sarimax.ipynb) deja el
# ciclo semanal a la parte estacional, y sus residuos siguen correlacionados en los rezagos 21 y 28.
# Aquí se le agregan seis indicadores del día de la semana, junto al festivo, sin cambiar los
# órdenes (1,1,2)(0,0,2)7 ni nada más. Las funciones son las del notebook 5.
#
# 1. Validación 2020-2022 de la versión nueva, contra la que quedó fijada (etapa4_comun.csv.gz),
#    con la misma regla: la versión con más variables entra solo si gana con Diebold-Mariano
#    p < 0,05. Ljung-Box de los residuos de las dos versiones, a 14, 21 y 28 rezagos.
# 2. La versión fijada, otra vez en la prueba pero con diez pasos, para tener h = 10 (la semana
#    h = 4 a 10 es la que se podría pronosticar si el precio llegara con tres días de atraso).
#    Sus pronósticos de h = 3 a 9 tienen que coincidir con los guardados.
# 3. Si la versión nueva gana en validación, se corre también en la prueba, como corrección
#    posterior: la versión de la tesis sigue siendo la que se fijó antes de la prueba.
#
# Salidas, en resultados/modelo_sarimax_dia_semana/.
suppressPackageStartupMessages({
  library(forecast)
  library(data.table)
  library(parallel)
  library(jsonlite)
})
setDTthreads(4)

PANELES <- "paneles"
VIEJO <- "resultados/modelo_sarimax"
SALIDA <- "resultados/modelo_sarimax_dia_semana"
# Con LIMPIO=1 corre las dos versiones en el periodo limpio (paso 9g), sobre los paneles actualizados
LIMPIO <- Sys.getenv("LIMPIO") == "1"
if (LIMPIO) {
  PANELES <- "periodo_limpio/paneles"
  SALIDA <- "resultados/periodo_limpio/sarimax"
}
dir.create(SALIDA, recursive = TRUE, showWarnings = FALSE)

HORAS <- 1:24
HORIZONTES <- 3:10
PASOS <- max(HORIZONTES)
INICIO <- as.Date("2015-03-01")
FIN_ELECCION <- as.Date("2019-12-31")
ORIGEN_FINAL <- as.Date("2026-10-06")
NUCLEOS <- 10
NIVEL <- 0.05
PERIODOS <- list("2020_2022" = c("2020-01-01", "2022-12-31"), "2023_2025" = c("2023-01-01", "2025-12-31"),
                 "2026" = c("2026-01-01", "2026-10-06"))

tabla <- fread(file.path(PANELES, "panel_horario_modelo.csv.gz"),
               select = c("fecha", "hora", "lp", "es_festivo", paste0("es_festivo_h", c(1:7, 14, 30))))
tabla[, fecha := as.Date(fecha)]
setorder(tabla, fecha, hora)
if (LIMPIO) {
  ORIGEN_FINAL <- max(tabla$fecha)
  PERIODOS <- list(limpio = c("2026-10-01", as.character(ORIGEN_FINAL)))
}
stopifnot(nrow(tabla) == uniqueN(tabla$fecha) * 24, min(tabla$fecha) == INICIO, max(tabla$fecha) == ORIGEN_FINAL)

FECHAS <- seq(INICIO, ORIGEN_FINAL + 14, by = "day")
LP <- matrix(NA_real_, length(FECHAS), 24)
LP[seq_len(uniqueN(tabla$fecha)), ] <- matrix(tabla$lp, ncol = 24, byrow = TRUE)
dia <- tabla[hora == 1]
FEST <- rep(NA_real_, length(FECHAS))
FEST[match(dia$fecha, FECHAS)] <- dia$es_festivo
for (k in c(1:7, 14)) {
  j <- match(dia$fecha + k, FECHAS)
  FEST[j[!is.na(j)]] <- dia[[paste0("es_festivo_h", k)]][!is.na(j)]
}
stopifnot(!anyNA(FEST))
# seis indicadores del día de la semana; el lunes queda de referencia
SEMANA <- sapply(2:7, function(d) as.numeric(as.integer(format(FECHAS, "%u")) == d))
colnames(SEMANA) <- c("martes", "miercoles", "jueves", "viernes", "sabado", "domingo")

config <- fromJSON(file.path(VIEJO, "configuracion_final.json"))
stopifnot(config$version == "comun", length(config$exogenas) == 0)
ORDEN <- as.integer(config$ordenes[1, c("p", "d", "q", "P", "D", "Q")])
stopifnot(nrow(unique(config$ordenes)) == 1)

diseno <- function(i, version) {
  m <- matrix(FEST[i], ncol = 1, dimnames = list(NULL, "festivo"))
  if (version == "dia_semana") m <- cbind(m, SEMANA[i, , drop = FALSE])
  m
}

ajustar <- function(H, fin, version) {
  i <- seq_len(match(fin, FECHAS))
  y <- ts(LP[i, H], frequency = 7)
  xr <- diseno(i, version)
  est <- function(m) Arima(y, order = ORDEN[1:3], seasonal = list(order = ORDEN[4:6], period = 7), xreg = xr, method = m)
  tryCatch(est("CSS-ML"), error = function(e) est("ML"))
}

pronosticar <- function(fit, H, t, version) {
  i <- seq_len(match(t, FECHAS))
  n <- length(i)
  actual <- Arima(ts(LP[i, H], frequency = 7), model = fit, xreg = diseno(i, version))
  f <- forecast(actual, xreg = diseno(n + seq_len(PASOS), version), h = PASOS, level = 80)
  data.frame(fecha = FECHAS[n], hora = H, h = HORIZONTES, lp_hat = as.numeric(f$mean)[HORIZONTES],
             lo80 = as.numeric(f$lower)[HORIZONTES], hi80 = as.numeric(f$upper)[HORIZONTES])
}

una_hora <- function(H, version, cortes, fin) {
  siguientes <- c(cortes[-1], fin + 1)
  salida <- list()
  previo <- NULL
  fallos <- 0L
  for (k in seq_along(cortes)) {
    origenes <- FECHAS[FECHAS >= cortes[k] & FECHAS < siguientes[k] & FECHAS + min(HORIZONTES) <= fin]
    if (!length(origenes)) next
    fit <- tryCatch(ajustar(H, cortes[k] - 1, version), error = function(e) NULL)
    if (is.null(fit)) {
      fallos <- fallos + 1L
      fit <- previo
    }
    previo <- fit
    for (j in seq_along(origenes)) salida[[length(salida) + 1]] <- pronosticar(fit, H, origenes[j], version)
  }
  r <- do.call(rbind, salida)
  list(pred = r[r$fecha + r$h <= fin, ], fallos = fallos)
}

ljung <- function(H, version) {
  f <- ajustar(H, FIN_ELECCION, version)
  sapply(c(14, 21, 28), function(L) Box.test(residuals(f), lag = L, type = "Ljung-Box", fitdf = sum(ORDEN[c(1, 3, 4, 6)]))$p.value)
}

con_nucleos <- function(f) {
  cl <- makeCluster(NUCLEOS)
  on.exit(stopCluster(cl))
  clusterEvalQ(cl, suppressPackageStartupMessages(library(forecast)))
  clusterExport(cl, c("LP", "FEST", "SEMANA", "FECHAS", "PASOS", "HORIZONTES", "ORDEN", "FIN_ELECCION",
                      "diseno", "ajustar", "pronosticar", "una_hora", "ljung"), envir = globalenv())
  f(cl)
}

correr <- function(version, periodo) {
  ruta <- file.path(SALIDA, sprintf("%s_%s.csv.gz", version, periodo))
  if (file.exists(ruta)) return(fread(ruta)[, fecha := as.Date(fecha)][])
  t0 <- Sys.time()
  lim <- as.Date(PERIODOS[[periodo]])
  cortes <- seq(lim[1], lim[2], by = "month")
  r <- con_nucleos(function(cl) parLapplyLB(cl, HORAS, una_hora, version, cortes, lim[2], chunk.size = 1))
  p <- rbindlist(lapply(r, `[[`, "pred"))
  setorder(p, fecha, hora, h)
  fwrite(p, ruta)
  cat(sprintf("%s, %s: %d pronósticos, %d meses sin converger, %.0f min\n", version, periodo, nrow(p),
              sum(sapply(r, `[[`, "fallos")), as.numeric(difftime(Sys.time(), t0, units = "mins"))))
  p[, fecha := as.Date(fecha)][]
}

completar <- function(p) {
  d <- copy(p)
  d[, i := match(fecha, FECHAS)]
  d[, lp_t := LP[cbind(i, hora)]]
  d[, y := LP[cbind(i + h, hora)] - lp_t]
  d[, y_hat := lp_hat - lp_t]
  stopifnot(!anyNA(d$y), !anyNA(d$y_hat))
  d[]
}

rmse <- function(e) sqrt(mean(e ^ 2))

diebold_mariano <- function(e_a, e_b, fechas, L) {
  d <- as.numeric(tapply(e_a ^ 2 - e_b ^ 2, fechas, mean))
  n <- length(d)
  u <- d - mean(d)
  v <- mean(u * u)
  for (l in seq_len(min(L, n - 1))) v <- v + 2 * (1 - l / (L + 1)) * mean(u[(l + 1):n] * u[1:(n - l)])
  t <- mean(d) / sqrt(v / n)
  c(t = t, p = 2 * pnorm(-abs(t)))
}

if (LIMPIO) {
  for (v in c("fijada", "dia_semana")) invisible(correr(v, "limpio"))
  quit(save = "no")
}

# ------------------------------------------------------------------ 1. validación de la versión nueva
nueva <- completar(correr("dia_semana", "2020_2022")[h <= 9])
fijada <- completar(fread(file.path(VIEJO, "etapa4_comun.csv.gz"))[, fecha := as.Date(fecha)])
setkey(nueva, fecha, hora, h); setkey(fijada, fecha, hora, h)
stopifnot(nrow(nueva) == nrow(fijada), all(nueva$fecha == fijada$fecha), all(nueva$h == fijada$h))
dm <- diebold_mariano(nueva$y - nueva$y_hat, fijada$y - fijada$y_hat, nueva$fecha, 9 - 1 + 7)
media_dia <- function(d) d[, e := y - y_hat][, .(nivel = mean(e)), by = .(fecha, h)]
forma <- function(d) { m <- d[, e := y - y_hat][, nivel := mean(e), by = .(fecha, h)]; rmse(m$e - m$nivel) }
validacion <- data.table(version = c("fijada (festivo)", "nueva (festivo y día de la semana)"),
                         rmse_log = c(rmse(fijada$y - fijada$y_hat), rmse(nueva$y - nueva$y_hat)),
                         rmse_ingenuo_dia = rmse(fijada$y),
                         forma = c(forma(fijada), forma(nueva)),
                         dm_t_contra_fijada = c(NA, dm[["t"]]), dm_p_contra_fijada = c(NA, dm[["p"]]))
validacion[, mejora := 100 * (1 - rmse_log / rmse_ingenuo_dia)]
GANA <- dm[["t"]] < 0 && dm[["p"]] < NIVEL
fwrite(validacion, file.path(SALIDA, "validacion.csv"))
print(validacion)
cat("La versión nueva", if (GANA) "gana" else "no gana", "en validación con la regla de la tabla 5\n")

lb <- con_nucleos(function(cl) {
  rbindlist(lapply(c("fijada", "dia_semana"), function(v) {
    m <- do.call(rbind, parLapplyLB(cl, HORAS, ljung, v, chunk.size = 1))
    data.table(version = v, hora = HORAS, p_14 = m[, 1], p_21 = m[, 2], p_28 = m[, 3])
  }))
})
fwrite(lb, file.path(SALIDA, "ljung_box.csv"))
print(lb[, .(sin_autocorrelacion_14 = sum(p_14 > NIVEL), sin_autocorrelacion_21 = sum(p_21 > NIVEL),
             sin_autocorrelacion_28 = sum(p_28 > NIVEL)), by = version])

# ------------------------------------------------------------------ 2. la versión fijada con h = 10
for (periodo in c("2023_2025", "2026")) {
  p <- correr("fijada", periodo)
  viejo <- fread(file.path(VIEJO, sprintf("prueba_%s.csv.gz", periodo)))[, fecha := as.Date(fecha)]
  j <- merge(p[h <= 9], viejo, by = c("fecha", "hora", "h"), suffixes = c("", "_viejo"))
  stopifnot(nrow(j) == nrow(viejo))
  cat(sprintf("%s: diferencia máxima con lo guardado en h = 3 a 9: %.2e\n", periodo, max(abs(j$lp_hat - j$lp_hat_viejo))))
}

# ------------------------------------------------------------------ 3. la versión nueva en la prueba
if (GANA) for (periodo in c("2023_2025", "2026")) invisible(correr("dia_semana", periodo))
writeLines(toJSON(list(gana_en_validacion = GANA, orden = ORDEN, horizontes = HORIZONTES), auto_unbox = TRUE),
           file.path(SALIDA, "decision.json"))
