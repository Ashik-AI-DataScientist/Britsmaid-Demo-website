/* Deliberately generic scenario assumptions; not local market data. */
(function (root) {
  function calculate(input) {
    var bedrooms = Number(input.bedrooms);
    var land = Number(input.land_cents || 0);
    if (!Number.isInteger(bedrooms) || bedrooms < 1 || bedrooms > 12 || !Number.isFinite(land) || land < 0 || land > 100000) throw new Error('Please enter 1–12 bedrooms and a valid land extent.');
    var amenities = Array.isArray(input.amenities) ? input.amenities : [];
    var premiums = {pool: 0.20, gym: 0.05, garden: 0.04, parking: 0.02, ac: 0.06, wifi: 0.03};
    var premium = Object.keys(premiums).reduce(function (sum, key) { return sum + (amenities.includes(key) ? premiums[key] : 0); }, 0);
    // Land contributes only up to 5%; more land alone does not imply more bookings.
    premium += Math.min(land, 50) / 50 * 0.05;
    var nightly = Math.round((1800 + bedrooms * 1100) * (1 + Math.min(premium, 0.45)));
    return {low: Math.round(nightly * 30 * 0.45 / 100) * 100, high: Math.round(nightly * 30 * 0.60 / 100) * 100, nightly: nightly, occupancy: [0.45, 0.60], model_version: 'generic-v1', currency: 'INR', basis: 'gross_booking_revenue'};
  }
  root.BritsmaidEarnings = {calculate: calculate};
  if (typeof module !== 'undefined') module.exports = root.BritsmaidEarnings;
})(typeof window !== 'undefined' ? window : globalThis);
