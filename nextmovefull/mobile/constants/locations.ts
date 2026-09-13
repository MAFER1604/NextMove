export interface PresetLocation {
  id: string;
  label: string;
  latitude: number;
  longitude: number;
}

// Coordenadas reales aproximadas, usadas como puntos fijos y deterministas
// (nunca generadas al azar en cada render).
export const CURRENT_LOCATION_PRESETS: PresetLocation[] = [
  { id: "depto-tec", label: "Departamento (Tec)", latitude: 25.6489, longitude: -100.2854 },
  { id: "centro", label: "Centro de Monterrey", latitude: 25.6714, longitude: -100.3095 },
  { id: "san-pedro", label: "San Pedro", latitude: 25.6512, longitude: -100.4025 },
  { id: "valle-oriente", label: "Valle Oriente", latitude: 25.6486, longitude: -100.3616 },
  { id: "mitras", label: "Mitras", latitude: 25.6842, longitude: -100.3564 },
];

export const DESTINATION_PRESETS: PresetLocation[] = [
  { id: "tec", label: "Tecnológico de Monterrey", latitude: 25.6514, longitude: -100.2895 },
  { id: "paseo-tec", label: "Paseo Tec", latitude: 25.6469, longitude: -100.2839 },
  { id: "nuevo-sur", label: "Nuevo Sur", latitude: 25.6398, longitude: -100.3157 },
  { id: "fundidora", label: "Parque Fundidora", latitude: 25.6789, longitude: -100.2844 },
  { id: "centro-mty", label: "Centro de Monterrey", latitude: 25.6714, longitude: -100.3095 },
  { id: "depto-tec-2", label: "Departamento Tec", latitude: 25.6489, longitude: -100.2854 },
];

// Zonas auxiliares para generar puntos de recogida/entrega plausibles
// alrededor de la ciudad (no se usan coordenadas aleatorias sin ancla real).
export const CITY_ANCHORS: PresetLocation[] = [
  { id: "obispado", label: "Obispado", latitude: 25.6746, longitude: -100.3389 },
  { id: "independencia", label: "Independencia", latitude: 25.6577, longitude: -100.3298 },
  { id: "contry", label: "Contry", latitude: 25.6355, longitude: -100.2825 },
  { id: "del-valle", label: "Del Valle", latitude: 25.6489, longitude: -100.3762 },
  { id: "la-alianza", label: "La Alianza", latitude: 25.6975, longitude: -100.2790 },
  ...CURRENT_LOCATION_PRESETS,
  ...DESTINATION_PRESETS,
];
