# Datos de las figuras de la sección 3.4 que 5_modelo_sarimax.ipynb no guardó: la correlación de cada
# variable con el precio antes y después del preblanqueo, y el diagnóstico de los residuos del modelo final.
# Usa las mismas funciones y los mismos datos del notebook, solo con 2015-2019, y no cambia nada del modelo:
# los órdenes salen de etapa2_ordenes.csv y la configuración final de configuracion_final.json.
# Uso: Rscript fig_sarimax_datos.R   (desde informe/codigo)
suppressPackageStartupMessages({
  library(data.table)
  library(forecast)
  library(jsonlite)
})

RAIZ <- normalizePath(file.path(getwd(), "..", ".."))
PANELES <- file.path(RAIZ, "paneles")
SARIMAX <- file.path(RAIZ, "resultados", "modelo_sarimax")
SALIDA <- file.path(RAIZ, "informe", "figuras")

HORAS <- 1:24
REZAGO <- 9
INICIO <- as.Date("2015-03-01")
FIN_ELECCION <- as.Date("2019-12-31")
NIVEL <- 0.05

# ----------------------------------------------------------------------------- datos, como en el notebook
tabla <- fread(file.path(PANELES, "panel_horario_modelo.csv.gz"), select = c("fecha", "hora", "lp", "es_festivo"))
tabla[, fecha := as.Date(fecha)]
tabla <- tabla[fecha <= FIN_ELECCION]
setorder(tabla, fecha, hora)
FECHAS <- seq(INICIO, FIN_ELECCION, by = "day")
stopifnot(nrow(tabla) == length(FECHAS) * 24)
LP <- matrix(tabla$lp, ncol = 24, byrow = TRUE)
FEST <- tabla[hora == 1, es_festivo]
n <- length(FECHAS)

candidatas <- fread(file.path(SARIMAX, "etapa3_candidatas.csv"))
vivas <- candidatas[motivo == "candidata", variable]
pc <- fread(file.path(PANELES, "panel_caracteristicas.csv.gz"), select = c("fecha", "hora", vivas))
pc[, fecha := as.Date(fecha)]
setorder(pc, fecha, hora)
filas <- match(FECHAS - REZAGO, unique(pc$fecha))
stopifnot(!anyNA(filas))
X <- setNames(lapply(vivas, function(v) {
  m <- matrix(as.numeric(pc[[v]]), ncol = 24, byrow = TRUE)
  for (H in HORAS) m[, H] <- nafill(m[, H], type = "locf")
  m[filas, ]
}), vivas)
rm(pc)

ordenes <- fread(file.path(SARIMAX, "etapa2_ordenes.csv"))
plan_hora <- as.matrix(ordenes[, .(p, d, q, P, D, Q)])

# ----------------------------------------------------------------------------- preblanqueo
# Igual a blanquear() del notebook, y además la correlación sin filtrar, en niveles
filas_pb <- rbindlist(lapply(HORAS, function(H) {
  o <- as.integer(plan_hora[H, ])
  m0 <- Arima(ts(LP[, H], frequency = 7), order = o[1:3], seasonal = list(order = o[4:6], period = 7),
              method = "CSS-ML")
  ry <- as.numeric(residuals(m0))
  fuera <- seq_len(max(1L, sum(o[c(1, 2)]) + 7L * sum(o[c(4, 5)])))
  rbindlist(lapply(vivas, function(v) {
    x <- X[[v]][, H]
    rx <- tryCatch(as.numeric(residuals(Arima(ts(x, frequency = 7), model = m0))), error = function(e) NULL)
    blanca <- if (is.null(rx) || sd(rx[-fuera]) == 0) 0 else cor(ry[-fuera], rx[-fuera])
    cruda <- if (sd(x) == 0) 0 else cor(LP[, H], x)
    data.table(hora = H, variable = v, cruda = cruda, preblanqueada = blanca)
  }))
}))
limite <- qnorm(1 - NIVEL / (2 * length(vivas))) / sqrt(n)
horas <- filas_pb[, .(horas_signif = sum(abs(preblanqueada) > limite)), by = variable]
revisar <- merge(horas, candidatas[, .(variable, guardadas = horas_signif)], by = "variable")
cat(sprintf("preblanqueo: %d días, umbral %.4f; coincide con el notebook en %d de %d variables\n",
            n, limite, sum(revisar$horas_signif == revisar$guardadas), nrow(revisar)))
fwrite(filas_pb, file.path(SALIDA, "datos_sarimax_preblanqueo.csv"))

# ----------------------------------------------------------------------------- residuos del modelo final
final <- fromJSON(file.path(SARIMAX, "configuracion_final.json"))
stopifnot(length(final$exogenas) == 0)
o <- as.integer(unlist(final$ordenes[1, c("p", "d", "q", "P", "D", "Q")]))
diag <- rbindlist(lapply(HORAS, function(H) {
  xr <- matrix(FEST, ncol = 1, dimnames = list(NULL, "festivo"))
  y <- ts(LP[, H], frequency = 7)
  f <- tryCatch(Arima(y, order = o[1:3], seasonal = list(order = o[4:6], period = 7), xreg = xr, method = "CSS-ML"),
                error = function(e) Arima(y, order = o[1:3], seasonal = list(order = o[4:6], period = 7), xreg = xr,
                                          method = "ML"))
  r <- residuals(f)
  lb <- Box.test(r, lag = 14, type = "Ljung-Box", fitdf = sum(o[c(1, 3, 4, 6)]))$p.value
  fac <- acf(as.numeric(r)[-1], lag.max = 28, plot = FALSE)$acf[-1]
  data.table(hora = H, ljung_box_p = lb, rezago = 1:28, fac = fac)
}))
cat(sprintf("Ljung-Box: %d de 24 horas sin autocorrelación al 5%%\n", sum(unique(diag[, .(hora, ljung_box_p)])$ljung_box_p >= 0.05)))
fwrite(diag, file.path(SALIDA, "datos_sarimax_residuos.csv"))
