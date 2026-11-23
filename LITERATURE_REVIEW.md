# Literature Review

## 1. Groundwater Assessment in India

Groundwater is the primary source of irrigation and drinking water for a large
share of India's population. National resource assessments follow the
Ground Water Resource Estimation Committee (GEC-2015) methodology, which
estimates annual recharge, natural discharge, extractable resource, total
extraction and the stage of groundwater extraction for each assessment unit.

The stage of groundwater extraction compares total annual extraction with the
annual extractable resource. Assessment units are commonly classified as Safe
(≤ 70%), Semi-Critical (> 70% to 90%), Critical (> 90% to 100%) and
Over-Exploited (> 100%). These thresholds provide a consistent basis for
comparing groundwater stress across districts and talukas.

## 2. Groundwater Depletion and Stress

Satellite-based studies have documented significant groundwater depletion in
north-western and peninsular India. Rodell et al. (2009) used GRACE satellite
observations to estimate groundwater loss in Rajasthan, Punjab and Haryana,
while Asoka et al. (2017) separated the effects of monsoon rainfall and
pumping on groundwater storage changes. Both studies highlight the importance
of combining water-balance indicators with long-term observations.

## 3. Maharashtra Context

Maharashtra shows considerable regional variation in groundwater availability
and extraction. Western Maharashtra and parts of Marathwada include
assessment units under semi-critical, critical and over-exploited categories,
while some eastern districts retain relatively larger extractable resources.
CGWB assessments of Maharashtra report district and taluka-level resource
estimates that support regional comparison and planning.

Recent local studies, such as Kale et al. (2025), examine spatio-temporal
changes in groundwater levels in the Palghar and Thane districts of the North
Konkan region. Such work demonstrates the value of consistent, region-specific
trend analysis.

## 4. Analytical Approach in JALNETRA

JALNETRA converts CGWB-style resource assessment records into an interactive
analytical platform. The dashboard reports recharge, extractable resource,
total extraction, extraction stage and groundwater category for available
districts and talukas. Historical trends are examined for 2021–2025, and
XGBoost regression models with lag, rolling-average and growth features are
used to project indicators for 2026–2030. Projections are presented as
model-generated estimates rather than official forecasts.

The platform is intended for research, education and exploratory analysis. It
does not replace official groundwater assessments or regulatory decisions.

## References

1. Central Ground Water Board (CGWB). *Ground Water Resource Assessment
   Methodology (GEC-2015).* Ministry of Jal Shakti, Government of India.
2. Rodell, M., Velicogna, I., & Famiglietti, J. S. (2009). Satellite-based
   estimates of groundwater depletion in India. *Nature*, 460, 999–1002.
   DOI: 10.1038/nature08238.
3. Asoka, A., Gleeson, T., Wada, Y., & Mishra, V. (2017). Relative
   contribution of monsoon precipitation and pumping to changes in
   groundwater storage in India. *Nature Geoscience*, 10, 109–117.
4. Central Ground Water Board (2025). *Dynamic Ground Water Resources of
   Maharashtra — Assessment 2024.*
5. Kale, A. A., et al. (2025). Spatio-Temporal Variation of Groundwater Table
   in the Palghar and Thane Districts of the North Konkan Region. *Journal of
   Agricultural Research and Technology*, 50(3), 286–298.
