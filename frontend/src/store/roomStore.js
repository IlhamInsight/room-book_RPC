import { create } from "zustand";
import { callRPC } from "../utils/rpcClient";
import { getMediaUrl } from "../utils/media";

export const useRoomStore = create((set, get) => ({
  rooms: [],
  amenityTypes: [],
  isLoading: false,
  error: null,

  // Filter state
  filters: {
    searchTerm: "",
    priceRange: 1000000, // max price
    capacity: [],
    amenities: [],
  },

  // Actions
  setFilters: (newFilters) =>
    set((state) => ({
      filters: { ...state.filters, ...newFilters },
    })),

  fetchRooms: async () => {
    set({ isLoading: true, error: null });
    try {
      // Remote Procedure Call: room.get_list
      const roomData = await callRPC("room.get_list");

      if (!Array.isArray(roomData)) {
        throw new Error("Invalid data format from RPC Server");
      }

      // Transform data if necessary to match frontend expectations
      const rooms = roomData.map((room) => ({
        ...room,
        // Ensure price is a number
        price: parseFloat(room.price_per_hour),
        image:
          getMediaUrl(room.image) ||
          "https://images.unsplash.com/photo-1497366216548-37526070297c?auto=format&fit=crop&w=800&q=80",
        // Use dynamic rating from API (calculated from real reviews)
        rating: room.average_rating ? parseFloat(room.average_rating).toFixed(1) : 0,
        reviews: room.review_count || 0,
        // Map amenities to simple string array for easier filtering on frontend
        amenityNames:
          Array.isArray(room.amenities) ?
            room.amenities.map((a) => (typeof a === "string" ? a : a.name))
          : [],
        rawAmenities: Array.isArray(room.amenities) ? room.amenities : [],
      }));
      set({ rooms, isLoading: false, error: null });
    } catch (error) {
      console.error("Error fetching rooms via RPC:", error);
      const errorMsg =
        error.message ||
        "Failed to fetch rooms. Please check your connection.";
      set({
        error: errorMsg,
        isLoading: false,
      });

      // Keep existing rooms on error instead of clearing
      set({ rooms: get().rooms });
    }
  },

  fetchAmenities: async () => {
    try {
      // Remote Procedure Call: room.get_amenities
      const data = await callRPC("room.get_amenities");
      set({ amenityTypes: data || [] });
    } catch (error) {
      console.error("Error fetching amenities via RPC:", error);
    }
  },

  getRoomById: (id) => {
    return get().rooms.find((r) => r.id === parseInt(id));
  },

  getFilteredRooms: () => {
    const { rooms, filters } = get();

    return rooms.filter((room) => {
      // Search term
      const matchesSearch =
        room.name.toLowerCase().includes(filters.searchTerm.toLowerCase()) ||
        room.location.toLowerCase().includes(filters.searchTerm.toLowerCase());

      // Price
      const matchesPrice = room.price <= filters.priceRange;

      // Capacity
      let matchesCapacity = true;
      if (filters.capacity.length > 0) {
        matchesCapacity = filters.capacity.some((capStr) => {
          if (capStr === "1-4 People")
            return room.capacity >= 1 && room.capacity <= 4;
          if (capStr === "5-10 People")
            return room.capacity >= 5 && room.capacity <= 10;
          if (capStr === "10-20 People")
            return room.capacity > 10 && room.capacity <= 20;
          if (capStr === "20+ People") return room.capacity > 20;
          return false;
        });
      }

      // Amenities
      let matchesAmenities = true;
      if (filters.amenities.length > 0) {
        matchesAmenities = filters.amenities.every(
          (amenity) =>
            room.amenityNames.includes(amenity) ||
            // Handle slight naming mismatches between mock and db
            (amenity === "WiFi" && room.amenityNames.includes("WiFi")) ||
            (amenity === "Coffee / Tea" &&
              room.amenityNames.includes("Coffee / Tea")) ||
            (amenity === "Air Conditioning" &&
              room.amenityNames.includes("Air Conditioning")),
        );
      }

      return (
        matchesSearch && matchesPrice && matchesCapacity && matchesAmenities
      );
    });
  },
}));
